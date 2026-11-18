#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""aw — AlonWorkflow 最小核心（只依赖 Python 3.8+ 标准库）。

人在场时，引擎只为两类事背书；阶段顺序、人工确认、评审方法、TDD 纪律、知识库都交给 prompt、模板和人：
  (a) 模型不可信、人又不会去查的客观事实：测试真跑过且通过、TC 出现在测试报告里、代码已提交、评审之后代码没再变；
  (b) 便宜的确定性检查：阶段文件与小节、TC 表、[待确认]、[no-test] 清单。
没有状态机：进度从 specs/<spec>/ 下的文件推导；证据写进 specs/<spec>/evidence/*.json，都绑定代码指纹。

  python3 .aw/aw.py new <module> [--type feature|ui|refactor|bugfix] [--add <阶段>]...
  python3 .aw/aw.py retype [<spec>] [--type <类型>] [--add <阶段>]... [--drop <阶段>]...
  python3 .aw/aw.py check [<spec>] [--phase <阶段>] [--all]
  python3 .aw/aw.py verify [<spec>]
  python3 .aw/aw.py review run [<spec>] [--base <rev>]
  python3 .aw/aw.py review waive [<spec>] <理由>
  python3 .aw/aw.py close [<spec>] [--check]
  python3 .aw/aw.py status [--json]
  python3 .aw/aw.py ci
<spec> 省略时取 specs/ 下最新一个未关闭的 spec。退出码：0 通过；1 有问题（逐条打印，带出路）。
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION = "0.7.0"
AW = Path(__file__).resolve().parent
ROOT = AW.parent
TC_RE = re.compile(r"\bTC-(\d+)\b")
TC_HEAD_RE = re.compile(r"^#{2,6}\s*TC-(\d+)\b", re.M)
TC_NAME_RE = re.compile(r"(?i)(?<![A-Za-z])TC[-_]?(\d{1,4})(?!\d)")    # 用例名里的 TC 编号：TC-001 / TC001_x / test_tc001_x
TASK_RE = re.compile(r"^\s*- \[[ xX]\]\s*(TASK-[A-Za-z0-9]*-?\d+)\b(.*)$")
DECIDED = ("已确认", "已忽略")
# 定规则的文件：永远进代码指纹（改了 verify / 评审就要重来），close 和 ci 打印它们相对基线的差异（只提示，不拦）
RULE_FILES = (".aw/config.json", ".aw/test-presets.json")
WATCHED = RULE_FILES + (".github/",)
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".eggs", ".cache", "node_modules",
             ".venv", "venv", "htmlcov", "coverage", "testresults", ".next"}


# ---------------------------------------------------------------- 基础
def say(msg):
    print("[aw] " + msg)


def die(msg):
    print("[aw] ✗ " + msg, file=sys.stderr)
    sys.exit(1)


def fail(problems, title="问题"):
    print("[aw] ✗ {} 个{}：\n  - ".format(len(problems), title) + "\n  - ".join(problems), file=sys.stderr)
    sys.exit(1)


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def rel(p):
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def read(p):
    return Path(p).read_text(encoding="utf-8", errors="replace")


def load_json(p):
    try:
        return json.loads(read(p))
    except FileNotFoundError:
        return None
    except ValueError as e:
        die("{} 不是合法 JSON：{}".format(rel(p), e))


def write_json(p, doc):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(p))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


_CACHE = {}


def cached(name, path, hint):
    if name not in _CACHE:
        doc = load_json(path)
        if doc is None:
            die("{} 不存在：{}".format(rel(path), hint))
        _CACHE[name] = doc
    return _CACHE[name]


def conf():
    return cached("conf", AW / "config.json", "先在项目根目录执行 alonwf init")


def phases_def():
    return cached("phases", AW / "phases.json", "执行 alonwf update 补齐")


def presets():
    return cached("presets", AW / "test-presets.json", "执行 alonwf update 补齐")


def specs_root():
    return ROOT / conf().get("specs_dir", "specs")


# ---------------------------------------------------------------- spec
def all_specs():
    r = specs_root()
    if not r.is_dir():
        return []
    return sorted((p.resolve() for p in r.iterdir() if (p / "spec.json").is_file()), key=lambda p: (p.name.rsplit("_", 1)[-1], p.name))


def is_closed(d):
    return (d / "evidence/closed.json").is_file()


def pick(arg):
    if arg:
        for c in (ROOT / arg, specs_root() / arg):
            if (c / "spec.json").is_file():
                return c.resolve()
        die("{} 不是 aw spec（目录里没有 spec.json）。新需求用 `python3 .aw/aw.py new <module>` 创建".format(arg))
    open_ = [d for d in all_specs() if not is_closed(d)]
    if not open_:
        die("没有未关闭的 spec：`python3 .aw/aw.py new <module>` 新建，或在命令后写 spec 目录")
    return open_[-1]


def meta(d):
    m = load_json(d / "spec.json") or {}
    order = phases_def()["order"]
    bad = [p for p in m.get("phases", []) if p not in order]
    if m.get("type") not in phases_def()["types"] or bad:
        die("{}/spec.json 的 type 或 phases 不认识（type={}，未知阶段：{}）".format(rel(d), m.get("type"), ", ".join(bad) or "无"))
    return m


def gate(m, ph):
    pj = phases_def()
    g = json.loads(json.dumps(pj["phases"][ph]))
    ov = pj["types"][m["type"]].get("override", {}).get(ph, {})
    for f, mk in ov.get("required", {}).items():
        if mk is None:
            g["required"].pop(f, None)
        else:
            g["required"][f] = mk
    if "any_of" in ov:
        g["any_of"] = ov["any_of"]
    return g


def tasks_file(d, m):
    return d / gate(m, "tech-tasks")["dir"] / "tasks.md"


# ---------------------------------------------------------------- (b) 确定性检查
def marker_ok(mk, text):
    return re.search(mk[3:], text, re.M) is not None if mk.startswith("re:") else mk in text


def phase_problems(d, m, ph):
    g = gate(m, ph)
    base, mb, out = d / g["dir"], phases_def().get("min_bytes", 120), []

    def chk(name, markers):
        f = base / name
        if not f.is_file() or f.stat().st_size < mb:
            return ["{}/{}（缺失或内容过短）".format(g["dir"], name)]
        t = read(f)
        return ["{}/{} 缺少「{}」".format(g["dir"], name, mk[3:] if mk.startswith("re:") else mk)
                for mk in markers if not marker_ok(mk, t)]

    for name, markers in g.get("required", {}).items():
        out += chk(name, markers)
    for grp in g.get("any_of", []):
        if all(chk(n, []) for n in grp):
            out.append("{}/ 下至少要有其一：{}".format(g["dir"], " / ".join(grp)))
    extra = {"requirements-analysis": amb_problems, "interaction-design": uxamb_problems,
             "tech-tasks": task_problems, "test-verification": tc_problems}.get(ph)
    if extra:
        out += extra(d, m, g)
    return ["[{}] {}".format(ph, p) for p in out]


def section_table(text, word):
    """标题含 word 的第一个小节里的第一个表格：(表头, 数据行)。"""
    lines, head, rows = text.splitlines(), None, []
    start = next((i for i, ln in enumerate(lines) if re.match(r"#{1,6}\s", ln) and word in ln), None)
    if start is None:
        return None, []
    level = len(lines[start]) - len(lines[start].lstrip("#"))
    for ln in lines[start + 1:]:
        h = re.match(r"(#{1,6})\s", ln)
        if h and len(h.group(1)) <= level:
            break
        s = ln.strip()
        if not s.startswith("|"):
            if head is not None:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if head is None:
            head = cells
        elif any(cells):
            rows.append(cells)
    return head, rows


def undecided(label, status):
    if not any(x in (status or "") for x in DECIDED) or "待确认" in (status or ""):
        return "{} 仍待确认（状态：{}）：问用户，把回答写进 answers.md，再把状态改成已确认 / 已忽略".format(label, status or "未写")
    return None


def amb_problems(d, m, g):
    f = d / g["dir"] / "requirements.md"
    if not f.is_file():
        return []
    head, rows = section_table(read(f), "需求澄清")
    if not rows:
        return []
    if "状态" not in head:
        return ["{}/requirements.md「需求澄清」表缺「状态」列".format(g["dir"])]
    si = head.index("状态")
    return [p for p in (undecided(r[0] or "AMB", r[si] if si < len(r) else "") for r in rows) if p]


def uxamb_problems(d, m, g):
    out = []
    for f in sorted((d / g["dir"]).glob("*.md")):
        for h in re.finditer(r"(?m)^#{2,6}\s*(UXAMB-[^\s：:（(]+)[^\n]*\n((?:(?!#{1,6}\s).*\n?)*)", read(f)):
            st = re.search(r"(?m)^\s*-?\s*状态[：:]\s*(.*)$", h.group(2))
            p = undecided(h.group(1), st.group(1).strip() if st else "")
            if p:
                out.append("{}：{}".format(f.name, p))
    return out


def parse_tasks(f):
    tasks, cur = {}, None
    if not f.is_file():
        return tasks
    for line in read(f).splitlines():
        t = TASK_RE.match(line)
        if t:
            cur, rest = t.group(1), t.group(2)
            tasks[cur] = {"title": rest.split("[no-test]")[0].strip(" ：:"), "no_test": "[no-test]" in rest,
                          "reason": rest.split("[no-test]", 1)[1].strip(" ：:，,；;—-") if "[no-test]" in rest else None,
                          "tcs": TC_RE.findall(rest)}
            continue
        if cur and line.strip():
            if re.match(r"^\S", line):
                cur = None
                continue
            low = line.strip().lstrip("-* ").strip()
            if "[no-test]" in low:
                tasks[cur]["no_test"] = True
            r = re.match(r"(?:免测理由|免测原因|理由)\s*[:：]\s*(.+)", low)
            if r:
                tasks[cur]["reason"] = r.group(1).strip()
            if re.match(r"(?i)tc\s*[:：]", low):
                tasks[cur]["tcs"] += TC_RE.findall(low)
    return tasks


def task_problems(d, m, g):
    return [] if parse_tasks(d / g["dir"] / "tasks.md") else ["{}/tasks.md 没有解析到 `- [ ] TASK-xxx` 任务".format(g["dir"])]


def no_test_lines(d, m):
    items = [(k, t) for k, t in parse_tasks(tasks_file(d, m)).items() if t["no_test"]]
    if not items:
        return []
    lines = ["  - {} {} — {}".format(k, t["title"], ("理由：" + t["reason"]) if t["reason"] else "（没写理由）") for k, t in items[:10]]
    more = ["  … 另 {} 个".format(len(items) - 10)] if len(items) > 10 else []
    return ["[aw] ℹ️ [no-test] 任务 {} 个（不写测试；请确认只涉及配置 / 文档 / 样式 / 脚手架，关键逻辑不要藏在这里）：".format(len(items))] + lines + more


TC_WORDS = sorted({"未通过": "fail", "通过": "pass", "passed": "pass", "pass": "pass", "✅": "pass", "failed": "fail",
                   "fail": "fail", "失败": "fail", "❌": "fail", "skipped": "skip", "skip": "skip", "跳过": "skip",
                   "未执行": "skip", "pending": "pending", "待执行": "pending", "⏳": "pending", "blocked": "blocked",
                   "阻塞": "blocked"}.items(), key=lambda kv: -len(kv[0]))
TC_LABEL = {"pass": "通过", "fail": "失败", "skip": "未执行", "pending": "待执行", "blocked": "阻塞"}


def tc_cell(cell):
    v, cats = cell.replace("`", " ").replace("*", " ").lower(), set()
    for w, c in TC_WORDS:
        if w in v:
            cats.add(c)
            v = v.replace(w, " ")
    return cats.pop() if len(cats) == 1 else None


def tc_table(text):
    """design.md →（定义的 TC {编号int: 原文}, 执行结果表 {编号int: 规范值}, 问题）。执行结果表由人或 aw-qa 回填，是人工 TC 的唯一来源。"""
    defined = {int(n): "TC-" + n for n in TC_HEAD_RE.findall(text)}
    mt = re.search(r"^##\s+执行结果[^\n]*\n", text, re.M)
    if not mt:
        return defined, {}, ["没有 `## 执行结果` 小节"]
    end = re.search(r"^#{1,2}\s", text[mt.end():], re.M)
    body = text[mt.end():mt.end() + end.start()] if end else text[mt.end():]
    results, probs, head = {}, [], None
    for ln in body.splitlines() + [""]:
        s = ln.strip()
        if not s.startswith("|"):
            head = None
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):
            continue
        if head is None:
            ti = next((i for i, c in enumerate(cells) if c.upper().startswith("TC")), None)
            ri = next((cells.index(n) for n in ("结果", "执行结果", "执行状态", "状态") if n in cells), None)
            head = (ti, ri)
            continue
        ti, ri = head
        if ti is None or ri is None or ti >= len(cells):
            continue
        raw = cells[ri] if ri < len(cells) else ""
        for n in TC_RE.findall(cells[ti]):
            v = tc_cell(raw)
            if v is None:
                probs.append("执行结果表里 TC-{} 的结果「{}」认不出（写 通过 / 失败 / 待执行 / 未执行 / 阻塞）".format(n, raw))
            elif int(n) in results and results[int(n)] != v:
                probs.append("执行结果表里 TC-{} 有两行，结果不一致".format(n))
            else:
                results[int(n)] = v
    if not head and not results:
        probs.append("`## 执行结果` 里没有同时带 TC 列和结果列的表")
    return defined, results, probs


def tc_problems(d, m, g):
    f = d / g["dir"] / "design.md"
    if not f.is_file():
        return []
    defined, results, out = tc_table(read(f))
    if not defined:
        return out + ["{}/design.md 没有 `### TC-NNN` 用例标题".format(g["dir"])]
    out += ["执行结果表里没有 {}（每个用例一行，没跑就写 待执行）".format(defined[n]) for n in sorted(set(defined) - set(results))]
    mp_f = d / g["dir"] / "tc-map.json"
    mp = load_json(mp_f)
    if not isinstance(mp, dict):
        return out + ["{}/tc-map.json 缺失或不是对象（格式：{{\"TASK-TD-001\": [\"TC-001\"]}}）".format(g["dir"])]
    tasks = parse_tasks(tasks_file(d, m))
    for tid, tcs in sorted(mp.items()):
        if tid not in tasks:
            out.append("tc-map.json 引用了 tasks.md 里没有的任务 {}".format(tid))
        out += ["tc-map.json 里 {} 的 {} 没在 design.md 定义".format(tid, tc) for tc in tcs
                if not TC_RE.match(str(tc)) or int(TC_RE.match(str(tc)).group(1)) not in defined]
    for tid, t in tasks.items():
        if not t["no_test"] and not (t["tcs"] or mp.get(tid)):
            out.append("{} 没有映射任何 TC（tc-map.json 或任务下的 `TC:` 行）；确实不用测试就标 [no-test] 并写理由".format(tid))
    return out


def spec_problems(d, m, only=None):
    out = []
    for ph in ([only] if only else m["phases"]):
        out += phase_problems(d, m, ph)
    return out


# ---------------------------------------------------------------- (a) 代码指纹与提交状态
def git(*args):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}     # GIT_DIR / GIT_INDEX_FILE 不能把 git 指到别处
    try:
        p = subprocess.run(["git"] + list(args), cwd=str(ROOT), capture_output=True, env=env)
    except OSError as e:
        die("找不到 git：{}".format(e))
    return p.returncode, p.stdout.decode("utf-8", "surrogateescape")


def match_any(p, prefixes):
    return any(p == x.rstrip("/") or p.startswith(x.rstrip("/") + "/") for x in prefixes)


def is_code(p):
    parts = [x.lower() for x in p.split("/")]
    if any(x in JUNK_DIRS for x in parts) or p.endswith((".pyc", ".pyo")) or \
            any(a in ("bin", "obj") and b in ("debug", "release") for a, b in zip(parts, parts[1:])):
        return False
    c = conf()
    if match_any(p, WATCHED):
        return True
    if match_any(p, list(c.get("exempt_paths", [])) + [c.get("specs_dir", "specs") + "/", ".aw/"]):
        return False
    cps = c.get("code_paths", ["."])
    return "." in cps or match_any(p, cps)


def manifest():
    rc, out = git("ls-files", "-z", "-co", "--exclude-standard")
    if rc != 0:
        die("不是 git 仓库（或 git 出错）：aw 用 git 列出业务代码，算代码指纹")
    m = {}
    for f in sorted(set(x for x in out.split("\0") if x)):
        if is_code(f):
            fp = ROOT / f
            m[f] = sha(fp) if fp.is_file() else "<missing>"
    return m


def fingerprint(m=None):
    m = manifest() if m is None else m
    return hashlib.sha256("".join("{}\0{}\n".format(f, m[f]) for f in sorted(m)).encode("utf-8", "surrogateescape")).hexdigest()


def commit_problems():
    rc, out = git("status", "--porcelain", "-z", "--untracked-files=all")
    if rc != 0:
        return ["git status 出错，无法确认业务代码已提交"]
    dirty, toks, i = set(), out.split("\0"), 0
    while i < len(toks):
        e, i = toks[i], i + 1
        if len(e) > 3:
            dirty.add(e[3:])
            if "R" in e[:2] or "C" in e[:2]:
                dirty.add(toks[i]) if i < len(toks) and toks[i] else None
                i += 1
    dirty = sorted(f for f in dirty if is_code(f))
    _, lv = git("ls-files", "-v", "-z")
    flagged = [x[2:] for x in lv.split("\0") if len(x) > 2 and (x[0] in "Ss" or x[0].islower()) and is_code(x[2:])]
    out = []
    if dirty:
        out.append("业务代码有未提交的改动（{} 个，暂存了也算）：{}{}；提交后重新 verify".format(
            len(dirty), "、".join(dirty[:10]), "…" if len(dirty) > 10 else ""))
    if flagged:
        out.append("这些文件带 skip-worktree / assume-unchanged，git 不报告它们的改动：{}（git update-index --no-skip-worktree --no-assume-unchanged <文件>）".format(
            "、".join(flagged[:10])))
    return out


def short(v, n=300):
    t = json.dumps(v, ensure_ascii=False)
    return t if len(t) <= n else t[:n] + "…"


def rules_sha():
    out = {f: (sha(ROOT / f) if (ROOT / f).is_file() else None) for f in RULE_FILES}
    out["reviewer"] = hashlib.sha256(json.dumps(conf().get("reviewer"), sort_keys=True).encode()).hexdigest()
    return out


def rules_diff(base):
    """规则文件相对 base 提交的差异 → (打印行, 改了的文件)。JSON 按顶层键对比，便于一眼看出改了什么。"""
    lines, changed = [], []
    for f in RULE_FILES:
        rc, old = git("show", "{}:{}".format(base, f))
        new = read(ROOT / f) if (ROOT / f).is_file() else None
        old = old if rc == 0 else None
        if old == new:
            continue
        changed.append(f)
        try:
            o, n = json.loads(old or "{}"), json.loads(new or "{}")
            keys = [k for k in sorted(set(o) | set(n)) if o.get(k) != n.get(k)]
            lines += ["{} · {}: {} → {}".format(f, k, short(o.get(k)), short(n.get(k))) for k in keys] or ["{} · 只改了格式".format(f)]
        except ValueError:
            lines.append("{} 整份变了（不是合法 JSON）".format(f))
    return lines, changed


def head():
    rc, out = git("rev-parse", "--verify", "-q", "HEAD")
    return out.strip() if rc == 0 else None


# ---------------------------------------------------------------- (a) 评审由引擎起的另一个进程做
# 评审结论只认两种来源：`review run`（引擎按 config.reviewer 起只读评审 CLI、自己解析裁决）和人写的 `review waive <理由>`。
# agent 自己写的 review.md / review.json 都不算。CLI 与模型写死在配置里，不按「作者是谁」去猜。
SEVERITIES = ("P0", "P1", "P2", "P3")
VERDICT_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["verdict", "blocking", "findings"],
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]}, "blocking": {"type": "integer", "minimum": 0},
        "findings": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["severity", "file", "line", "title"],
            "properties": {"severity": {"type": "string", "enum": list(SEVERITIES)}, "file": {"type": "string"},
                           "line": {"type": "integer", "minimum": 0}, "title": {"type": "string"}}}}}}
REVIEW_PROMPT = """你是独立的代码评审者，只读：不要修改、创建或删除任何文件。
评审需求 {spec} 的代码改动：`git diff {base} HEAD`（业务代码部分）。需求、设计和测试用例在 {spec}/ 下，先读它们再看代码。
{dims}只报真实存在的问题，每条写清 file 和 line。severity：P0 = 错误结果 / 数据损坏 / 安全问题；P1 = 不满足需求或明显缺陷；P2 = 可维护性；P3 = 建议。
最终回复只输出一个 JSON 对象，不要任何别的文字：
{{"verdict": "pass 或 fail", "blocking": P0 与 P1 的条数, "findings": [{{"severity": "P1", "file": "src/x.py", "line": 12, "title": "一句话说明问题"}}]}}
verdict 为 fail 当且仅当 blocking > 0；没有问题就输出 {{"verdict": "pass", "blocking": 0, "findings": []}}。"""


def extract_json(text):
    """自由文本里最后一个顶层 JSON 对象（容忍 ```json 围栏和前后说明）。"""
    dec, found, i = json.JSONDecoder(), None, 0
    while True:
        j = (text or "").find("{", i)
        if j < 0:
            return found
        try:
            obj, i = dec.raw_decode(text, j)
            found = obj if isinstance(obj, dict) else found
        except ValueError:
            i = j + 1


def parse_raw(cli, raw):
    """评审 CLI 的原始输出 → 裁决对象（不校验）。claude 用 --output-format json，codex 用 -o 写最后一条消息。"""
    if cli == "claude":
        doc = extract_json(raw) or {}
        if isinstance(doc.get("structured_output"), dict):
            return doc["structured_output"]
        return extract_json(doc.get("result") or "")
    return extract_json(raw)


def verdict_problems(v):
    """严格按 VERDICT_SCHEMA 校验（codex 的 --output-schema 实测不强制），外加 blocking / verdict 和 findings 一致。"""
    if not isinstance(v, dict):
        return ["没有找到 JSON 裁决"]
    out = ["多余字段 {}".format(k) for k in v if k not in ("verdict", "blocking", "findings")]
    out += ["缺字段 {}".format(k) for k in ("verdict", "blocking", "findings") if k not in v]
    fs, n = v.get("findings"), v.get("blocking")
    if not isinstance(fs, list):
        return out + ["findings 不是数组"]
    for i, f in enumerate(fs):
        if not isinstance(f, dict) or set(f) != {"severity", "file", "line", "title"} or f["severity"] not in SEVERITIES or \
                not isinstance(f["file"], str) or type(f["line"]) is not int or f["line"] < 0 or not str(f["title"]).strip():
            out.append("findings[{}] 不合 schema：{}".format(i, json.dumps(f, ensure_ascii=False)[:120]))
    if type(n) is not int or n < 0:
        out.append("blocking 不是非负整数")
    elif not out and n != sum(1 for f in fs if f["severity"] in ("P0", "P1")):
        out.append("blocking={} 与 P0/P1 条数不一致".format(n))
    if v.get("verdict") not in ("pass", "fail") or (type(n) is int and v.get("verdict") != ("fail" if n else "pass")):
        out.append("verdict={} 与 blocking 不一致".format(v.get("verdict")))
    return out


def reviewer_argv(cli, exe, model, prompt, out_file, schema_file):
    if cli == "codex":     # --ignore-user-config 会连 model_provider 一起丢掉（实测 401），只关 hooks 和 execpolicy 规则
        return [exe, "exec", "-s", "read-only", "--ephemeral", "--ignore-rules", "-c", "features.hooks=false", "--skip-git-repo-check",
                "-C", str(ROOT), "-m", model, "--output-schema", str(schema_file), "-o", str(out_file), prompt]
    # --bare 只认 ANTHROPIC_API_KEY（实测走代理时连不上）：只读用户级设置、关掉全部 hooks，工具只给只读的几样
    return [exe, "-p", "--model", model, "--setting-sources", "user", "--settings", '{"disableAllHooks": true}',
            "--permission-mode", "dontAsk", "--allowedTools", "Read", "Grep", "Glob", "Bash(git diff:*)", "Bash(git show:*)",
            "Bash(git log:*)", "--output-format", "json", "--json-schema", json.dumps(VERDICT_SCHEMA), "--no-session-persistence", prompt]


def review_problems(d, fp):
    """review_required 时 close 与 ci 共用的评审判断。"""
    rv = load_json(d / "evidence/review.json")
    if not rv:
        return ["还没有评审：`python3 .aw/aw.py review run`（引擎按 .aw/config.json 的 reviewer 起评审 CLI）；"
                "确实不评审，由人执行 `python3 .aw/aw.py review waive <理由>`"]
    out, raw = [], d / "evidence/review-raw.txt"
    if rv.get("by") == "waive":
        if len(str(rv.get("reason", "")).strip()) < 4:
            out.append("review waive 没写像样的理由")
    elif rv.get("by") != "aw review run":
        out.append("review.json 不是引擎写的（by={}）：评审结论只认 `aw.py review run` 和人写的 `review waive`".format(rv.get("by")))
    elif not raw.is_file() or sha(raw) != rv.get("raw_sha"):
        out.append("评审原始输出 evidence/review-raw.txt 缺失或被改过：重新 `aw.py review run`")
    else:
        v = parse_raw(rv.get("cli"), read(raw))
        if verdict_problems(v) or v.get("blocking") != rv.get("blocking"):
            out.append("review.json 与评审原始输出对不上：重新 `aw.py review run`")
        elif rv.get("blocking"):
            out.append("评审有 {} 个阻塞项：修复 → verify → 重新 `aw.py review run`".format(rv["blocking"]))
    if rv.get("code_fp") != fp:
        out.append("评审之后代码变了：重新 `aw.py review run`")
    return out


def review_line(d):
    rv = load_json(d / "evidence/review.json") or {}
    if rv.get("by") == "waive":
        return "评审已豁免（{} · {}）：{}".format(rv.get("who"), rv.get("at"), rv.get("reason"))
    if rv.get("by") == "aw review run":
        return "评审：{} {} · 模型 {} · 阻塞 {} · {}".format(rv.get("cli"), rv.get("version"), rv.get("model"), rv.get("blocking"), rv.get("at"))
    return "评审：无引擎评审证据"


def show(d, m, manual):
    """只展示、不拦截（close / close --check / ci 共用）：人合并时该看的几样。"""
    f = d / "approvals.md"
    text = read(f).split("## 撤销")[0] if f.is_file() else ""
    seen = set(re.findall(r"(?m)^\s*-\s*([\w-]+)\s*·", text))
    miss = [ph for ph in m["phases"] if ph not in seen]
    if miss:
        say("ℹ️ approvals.md 里没有用户确认的阶段：{}".format("、".join(miss)))
    if manual:
        say("ℹ️ 这些 TC 只有执行结果表（人工）背书，测试报告里没有：{}".format("、".join(manual)))
    say("ℹ️ " + review_line(d))


def cmd_review_run(d, args):
    bases, rest = opt(args, "--base")
    rc_ = conf().get("reviewer") or {}
    cli, model = rc_.get("cli"), rc_.get("model")
    if cli not in ("codex", "claude") or not model:
        die("没有配置评审者：在 .aw/config.json 写 \"reviewer\": {\"cli\": \"codex 或 claude\", \"model\": \"<模型名>\"}（建议选和开发时不同的模型）")
    exe = shutil.which(cli)
    if not exe:
        die("找不到评审 CLI {}（config.reviewer.cli）：装好它，或改 reviewer；确实不评审由人执行 review waive".format(cli))
    base = (bases or [meta(d).get("base")])[-1]
    if not base or git("rev-parse", "--verify", "-q", base + "^{commit}")[0] != 0:
        die("不知道从哪个提交开始评审（spec.json 没有 base）：`aw.py review run --base <提交或分支>`")
    try:
        version = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30).stdout.strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        version = "unknown"
    dims = sorted(rel(x) for x in (AW / "packs").glob("*/review-dimensions.json"))
    prompt = REVIEW_PROMPT.format(spec=rel(d), base=base, dims="评审维度见 {}。\n".format("、".join(dims)) if dims else "")
    tmp = AW / "tmp" / "review"
    shutil.rmtree(str(tmp), ignore_errors=True)
    tmp.mkdir(parents=True)
    out_file, schema_file = tmp / "last.txt", tmp / "schema.json"
    schema_file.write_text(json.dumps(VERDICT_SCHEMA), encoding="utf-8")
    to = int(rc_.get("timeout_sec", 900))
    before, t0 = manifest(), datetime.datetime.now()
    say("评审：{}（{}）模型 {}，最多等 {}s".format(cli, version, model, to))
    try:
        p = subprocess.run(reviewer_argv(cli, exe, model, prompt, out_file, schema_file), cwd=str(ROOT), capture_output=True,
                           text=True, timeout=to, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        die("评审超时（{}s，config.reviewer.timeout_sec）：判失败".format(to))
    raw = read(out_file) if cli == "codex" and out_file.is_file() else (p.stdout or "")
    v = parse_raw(cli, raw)
    probs = verdict_problems(v)
    if probs:
        die("评审 CLI 没给出合法裁决（exit {}）：{}；输出末尾：{}".format(p.returncode, "；".join(probs[:5]), (raw or p.stderr or "")[-400:]))
    if manifest() != before:
        die("评审期间业务代码变了：评审进程不该写文件，结果作废")
    ev = d / "evidence"
    ev.mkdir(parents=True, exist_ok=True)
    (ev / "review-raw.txt").write_text(raw, encoding="utf-8")
    (ev / "review-prompt.txt").write_text(prompt, encoding="utf-8")
    reported = sorted((extract_json(raw) or {}).get("modelUsage") or {}) if cli == "claude" else []
    write_json(ev / "review.json", {
        "by": "aw review run", "at": now(), "head": head(), "base": base, "code_fp": fingerprint(before), "cli": cli,
        "cli_path": exe, "version": version, "model": model, "model_reported": reported, "prompt_sha": sha(ev / "review-prompt.txt"),
        "raw_sha": sha(ev / "review-raw.txt"), "secs": (datetime.datetime.now() - t0).seconds, "verdict": v["verdict"],
        "blocking": v["blocking"], "findings": v["findings"]})
    for f in v["findings"]:
        print("  - {} {}:{} {}".format(f["severity"], f["file"], f["line"], f["title"]))
    if v["blocking"]:
        fail(["评审有 {} 个阻塞项：修复 → verify → 重新 review run".format(v["blocking"])], "阻塞")
    say("评审通过（{} · {}）：结论绑定当前代码指纹".format(cli, model))


def cmd_review_waive(d, words):
    reason = " ".join(words).strip()
    if len(reason) < 4:
        die("用法：aw.py review waive [<spec>] <理由>（理由会记进证据，close --check 和 ci 都会展示）")
    _, who = git("config", "user.name")
    write_json(d / "evidence/review.json", {"by": "waive", "at": now(), "head": head(), "code_fp": fingerprint(),
                                            "who": who.strip() or os.environ.get("USER", "?"), "reason": reason})
    say("已记录评审豁免：{}（代码再变就失效）".format(reason))


# ---------------------------------------------------------------- (a) 测试真跑过
def fill(v, **kw):
    if isinstance(v, list):
        return [fill(x, **kw) for x in v]
    for k, x in kw.items():
        v = v.replace("{" + k + "}", x)
    return v


def case_outcome(o):
    o = (o or "").lower()
    return "passed" if o in ("passed", "pass") else ("skipped" if o in ("notexecuted", "skipped", "pending", "todo", "disabled") else "failed")


def parse_report(fmt, path):
    """测试报告 → [(用例名, passed|failed|skipped)]；没有报告或解析不了返回 None。"""
    if not path.is_file():
        return None
    cases = []
    try:
        if fmt == "trx":
            for u in ET.parse(str(path)).getroot().iter():
                if u.tag.split("}")[-1] == "UnitTestResult":
                    cases.append((u.get("testName", ""), case_outcome(u.get("outcome"))))
        elif fmt == "junit":
            for tc in ET.parse(str(path)).getroot().iter("testcase"):
                kids = {k.tag for k in tc}
                o = "skipped" if "skipped" in kids else ("failed" if kids & {"failure", "error"} else "passed")
                cases.append(((tc.get("classname", "") + "::" + tc.get("name", "")).strip(":"), o))
        elif fmt == "jest-json":
            for su in json.loads(read(path)).get("testResults", []):
                if su.get("message") and not su.get("assertionResults"):
                    cases.append((su.get("name", "suite"), "failed"))
                for a in su.get("assertionResults", []):
                    cases.append((a.get("fullName") or a.get("title", ""), case_outcome(a.get("status"))))
        else:
            die("不认识的报告格式 {}（trx / junit / jest-json）".format(fmt))
    except (ET.ParseError, ValueError, AttributeError) as e:
        print("[aw] ⚠️ 报告解析失败 {}：{}".format(path, e), file=sys.stderr)
        return None
    return cases


def python_bin():
    for c in (".venv/bin/python", "venv/bin/python"):
        if (ROOT / c).exists():
            return str(ROOT / c)
    return sys.executable


def run_stack(st):
    st = dict(presets().get(st.get("preset", ""), {}), **st)
    if not st.get("run") or not st.get("report"):
        die("测试栈 {} 缺 run / report（preset 见 .aw/test-presets.json）".format(st.get("name")))
    rdir = AW / "tmp" / "verify" / re.sub(r"[^\w.-]", "_", st.get("name", "test"))
    shutil.rmtree(str(rdir), ignore_errors=True)
    rdir.mkdir(parents=True, exist_ok=True)
    rep = Path(fill(st["report"]["path"], report_dir=str(rdir)))
    argv = fill(list(st["run"]), report_dir=str(rdir), report=str(rep), python=st.get("python") or python_bin())
    env = dict(os.environ, **st.get("env", {}))
    say("执行（{}）：{}".format(st.get("cwd", "."), " ".join(argv)))
    try:
        p = subprocess.run(argv, cwd=str(ROOT / st.get("cwd", ".")), env=env, capture_output=True, text=True,
                           timeout=conf().get("timeout_sec", 1800))
        code, output = p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        code, output = 127, str(e)
    cases = parse_report(st["report"]["format"], rep)
    r = {"name": st.get("name"), "cmd": " ".join(argv), "exit": code, "report": cases is not None,
         "report_sha": sha(rep) if rep.is_file() else None}
    cases = cases or []
    for k in ("passed", "failed", "skipped"):
        r[k] = sum(1 for _, o in cases if o == k)
    r["failed_names"] = [n for n, o in cases if o == "failed"][:20]
    r["error"] = ("没有生成测试报告（{}）".format(rel(rep)) if cases == [] and not r["report"] else
                  "一个用例都没跑" if r["passed"] + r["failed"] == 0 else None)
    r["ok"] = code == 0 and r["failed"] == 0 and not r["error"]
    r["cases"] = cases
    if not r["ok"]:
        tail = "\n".join([ln for ln in output.splitlines() if ln.strip()][-30:])
        print("[aw] ⚠️ {} 没通过（exit {}{}）。输出末尾：\n{}".format(r["name"], code, "，" + r["error"] if r["error"] else "", tail),
              file=sys.stderr)
    return r


def run_tests():
    stacks = conf().get("test") or []
    if not stacks:
        die("没有配置测试：在 .aw/config.json 的 \"test\" 里加测试栈，例如 [{\"name\": \"dotnet\", \"preset\": \"dotnet\", \"cwd\": \".\"}]"
            "（预设见 .aw/test-presets.json）。没有测试，就证明不了代码能用")
    before = manifest()
    res = [run_stack(st) for st in stacks]
    after = manifest()
    tcs = {}
    for r in res:
        for name, o in r.pop("cases"):
            for n in set(TC_NAME_RE.findall(name)):
                k = "TC-" + n
                if o == "failed" or (o == "passed" and tcs.get(k) != "failed"):
                    tcs[k] = o
    stable = before == after
    if not stable:
        ch = sorted(f for f in set(before) | set(after) if before.get(f) != after.get(f))
        print("[aw] ⚠️ 跑测试期间业务代码变了（{}）：结果不能当证据。测试 / 构建产物请加进 .gitignore".format("、".join(ch[:10])),
              file=sys.stderr)
    return {"at": now(), "head": head(), "code_fp": fingerprint(after), "stable": stable,
            "ok": stable and all(r["ok"] for r in res), "exit": next((r["exit"] for r in res if r["exit"]), 0),
            "passed": sum(r["passed"] for r in res), "failed": sum(r["failed"] for r in res),
            "skipped": sum(r["skipped"] for r in res), "tcs": dict(sorted(tcs.items(), key=lambda kv: int(kv[0][3:]))),
            "rules": rules_sha(), "stacks": res}


# ---------------------------------------------------------------- close 的唯一判断
def close_problems(d, m):
    """能不能关闭只在这里判断。返回 (问题, 只有执行结果表背书的 TC)。"""
    out = spec_problems(d, m) + commit_problems()
    fp = fingerprint()
    v = load_json(d / "evidence/verify.json")
    if not v:
        out.append("还没有 verify：`python3 .aw/aw.py verify {}`".format(rel(d)))
    elif not v.get("ok"):
        out.append("最近一次 verify 没通过（通过 {} / 失败 {}）：修好后重新 `python3 .aw/aw.py verify`".format(v.get("passed"), v.get("failed")))
    elif v.get("code_fp") != fp:
        out.append("verify 之后代码变了：重新 `python3 .aw/aw.py verify`")
    if conf().get("review_required", True):
        out += review_problems(d, fp)
    manual = []
    tv = gate(m, "test-verification")
    f = d / tv["dir"] / "design.md"
    if "test-verification" in m["phases"] and f.is_file():
        defined, table, _ = tc_table(read(f))
        rep = {int(k[3:]): o for k, o in ((v or {}).get("tcs") or {}).items()}
        for n in sorted(defined):
            if rep.get(n) == "failed":
                out.append("{} 的测试失败（见 verify 输出）".format(defined[n]))
            elif rep.get(n) != "passed":
                if table.get(n) == "pass":
                    manual.append(defined[n])
                else:
                    out.append("{} 测试报告里没有、执行结果表里是「{}」：写测试（用例名带 TC 编号）后 verify，或人工执行后回填 通过".format(
                        defined[n], TC_LABEL.get(table.get(n), "没写")))
    return out, manual


# ---------------------------------------------------------------- 命令
def opt(args, name):
    vals = [args[i + 1] for i, a in enumerate(args[:-1]) if a == name]
    rest = [a for i, a in enumerate(args) if a != name and (i == 0 or args[i - 1] != name)]
    return vals, rest


def phase_list(kind, base, adds, drops):
    pj = phases_def()
    if kind not in pj["types"]:
        die("不认识的需求类型 {}（{}）".format(kind, " / ".join(pj["types"])))
    bad = [a for a in adds + drops if a not in pj["order"]]
    if bad or "intake" in drops:
        die("不认识或不能去掉的阶段 {}（{}）".format(", ".join(bad) or "intake", " / ".join(pj["order"])))
    return [p for p in pj["order"] if (p in base or p in adds) and p not in drops]


def cmd_new(args):
    types, rest = opt(args, "--type")
    adds, rest = opt(rest, "--add")
    if len(rest) != 1 or not re.match(r"^[\w.-]+$", rest[0]):
        die("用法：aw.py new <module> [--type feature|ui|refactor|bugfix] [--add <阶段>]")
    kind = (types or ["feature"])[-1]
    phases = phase_list(kind, phases_def()["types"].get(kind, {}).get("phases", []), adds, [])
    d = specs_root() / "{}_{:%Y%m%d%H%M%S}".format(rest[0], datetime.datetime.now())
    if d.exists():
        die("{} 已存在".format(rel(d)))
    write_json(d / "spec.json", {"module": rest[0], "type": kind, "phases": phases, "created": now(), "base": head()})
    say("新建 {}（{}）：{}".format(rel(d), kind, " → ".join(phases)))
    say("第一个阶段 {}，由 {} 产出".format(phases[0], phases_def()["phases"][phases[0]]["agent"]))


def cmd_retype(args):
    """intake 判定的类型 / SCOPE 与 new 时不同：换类型（阶段回到该类型默认）再增减阶段。"""
    types, rest = opt(args, "--type")
    adds, rest = opt(rest, "--add")
    drops, rest = opt(rest, "--drop")
    if len(rest) > 1 or not (types or adds or drops):
        die("用法：aw.py retype [<spec>] [--type <类型>] [--add <阶段>]... [--drop <阶段>]...")
    d = pick(rest[0] if rest else None)
    if is_closed(d):
        die("{} 已关闭，不能改类型".format(rel(d)))
    m = meta(d)
    kind = types[-1] if types else m["type"]
    base = phases_def()["types"].get(kind, {}).get("phases", []) if types else m["phases"]
    m["type"], m["phases"] = kind, phase_list(kind, base, adds, drops)
    write_json(d / "spec.json", m)
    say("{}（{}）：{}".format(rel(d), kind, " → ".join(m["phases"])))


def cmd_check(args):
    ph, rest = opt(args, "--phase")
    if "--all" in rest:
        out = []
        for d in all_specs():
            out += ["{}: {}".format(rel(d), p) for p in spec_problems(d, meta(d))]
        if out:
            fail(out)
        say("check 通过：{} 个 spec".format(len(all_specs())))
        return
    d = pick(rest[0] if rest else None)
    m = meta(d)
    if ph and ph[-1] not in m["phases"]:
        die("{} 不在这个 spec 的阶段里（{}）".format(ph[-1], " → ".join(m["phases"])))
    probs = spec_problems(d, m, ph[-1] if ph else None)
    if not ph or ph[-1] in ("tech-tasks", "test-verification"):
        for ln in no_test_lines(d, m):
            print(ln)
    if probs:
        fail(probs)
    say("check 通过：{}（{}）".format(rel(d), ph[-1] if ph else "全部阶段"))


def cmd_verify(args):
    d = pick(args[0] if args else None)
    rec = run_tests()
    write_json(d / "evidence/verify.json", rec)
    say("verify {}：通过 {} / 失败 {} / 跳过 {}；报告里的 TC：{} → {}".format(
        "通过" if rec["ok"] else "没通过", rec["passed"], rec["failed"], rec["skipped"],
        ", ".join("{} {}".format(k, v) for k, v in rec["tcs"].items()) or "无", rel(d / "evidence/verify.json")))
    sys.exit(0 if rec["ok"] else 1)


def cmd_review(args):
    sub, rest = (args[:1] or [""])[0], args[1:]
    if sub == "done":
        die("review done 已取消：自己写的 review.md 不算评审证据。用 `aw.py review run`（引擎起评审 CLI），或由人 `aw.py review waive <理由>`")
    if sub not in ("run", "waive"):
        die("用法：aw.py review run [<spec>] [--base <rev>] | review waive [<spec>] <理由>")
    _, pos = opt(rest, "--base")
    spec = pos[0] if pos and any((c / "spec.json").is_file() for c in (ROOT / pos[0], specs_root() / pos[0])) else None
    d = pick(spec)
    if sub == "run":
        cmd_review_run(d, [a for a in rest if a != spec])
    else:
        cmd_review_waive(d, [a for a in rest if a != spec])


def cmd_close(args):
    check = "--check" in args
    rest = [a for a in args if a != "--check"]
    d = pick(rest[0] if rest else None)
    m = meta(d)
    probs, manual = close_problems(d, m)
    for ln in no_test_lines(d, m):
        print(ln)
    show(d, m, manual)
    diff, changed = rules_diff(m["base"]) if m.get("base") else (["spec.json 没有 base，无法对比规则文件"], [])
    if diff:
        say("ℹ️ 规则文件相对 spec 开始时（{}）变了（只提示，不拦；合并时请人看一眼）：\n  - {}".format(
            (m.get("base") or "?")[:10], "\n  - ".join(diff)))
    if probs:
        fail(probs, "关闭前要解决的问题")
    if check:
        say("可以关闭：{}".format(rel(d)))
        return
    write_json(d / "evidence/closed.json", {"at": now(), "head": head(), "code_fp": fingerprint(), "manual_tcs": manual,
                                            "rules": rules_sha(), "rules_changed": changed})
    say("已关闭 {}：证据在 {}/evidence/，记得把 spec 一起提交".format(rel(d), rel(d)))


def spec_status(d):
    m = meta(d)
    cur = next((ph for ph in m["phases"] if phase_problems(d, m, ph)), None)
    fp = fingerprint()
    v, rv = load_json(d / "evidence/verify.json"), load_json(d / "evidence/review.json")
    return {"spec": rel(d), "type": m["type"], "phases": m["phases"], "current": cur, "closed": is_closed(d),
            "verify": "none" if not v else ("failed" if not v.get("ok") else ("ok" if v.get("code_fp") == fp else "stale")),
            "review": "none" if not rv else ("stale" if rv.get("code_fp") != fp else ("waived" if rv.get("by") == "waive" else
                                                                                      ("blocked" if rv.get("blocking") else "ok")))}


def cmd_status(args):
    st = [spec_status(d) for d in all_specs()]
    if "--json" in args:
        print(json.dumps(st, ensure_ascii=False, indent=2))
        return
    if not st:
        say("还没有 spec：`python3 .aw/aw.py new <module>`")
    for s in st:
        say("{}（{}）{} · 当前阶段 {} · verify {} · 评审 {}".format(
            s["spec"], s["type"], "已关闭" if s["closed"] else "进行中", s["current"] or "全部齐了", s["verify"], s["review"]))
    wf = ROOT / ".github/workflows"
    if not any("aw.py ci" in read(p) for p in (wf.glob("*.y*ml") if wf.is_dir() else [])):
        say("ℹ️ 没有跑 `aw.py ci` 的 CI：证据只在本机，没有不经过模型的见证者（alonwf doctor 有说明）")


def ci_base():
    b = os.environ.get("AW_CI_BASE") or ("origin/" + os.environ["GITHUB_BASE_REF"] if os.environ.get("GITHUB_BASE_REF") else "")
    if b and git("rev-parse", "--verify", "-q", b + "^{commit}")[0] == 0:
        return b
    say("ℹ️ 没有可用的基线（AW_CI_BASE / GITHUB_BASE_REF{}）：规则用当前分支的，不核对证据，只重跑测试、检查已关闭 spec 的文件".format(
        "：{} 解析不了".format(b) if b else ""))
    return None


def cmd_ci(args):
    """CI 是不经过模型的见证者：用基线分支的规则从零重跑测试，复核本分支新关闭的 spec 的证据。"""
    out, base, fp = [], ci_base(), fingerprint()          # 指纹按当前分支规则算：证据就是按它记的
    checked = []
    if base:
        diff, _ = rules_diff(base)
        if diff:
            say("ℹ️ 规则文件相对基线 {} 变了（只提示，合并前请人看）：\n  - {}".format(base, "\n  - ".join(diff)))
        now_code = manifest()
        for name, f in (("conf", ".aw/config.json"), ("presets", ".aw/test-presets.json")):
            rc, txt = git("show", "{}:{}".format(base, f))
            if rc == 0:
                try:
                    _CACHE[name] = json.loads(txt)
                except ValueError:
                    out.append("基线 {} 的 {} 不是合法 JSON".format(base, f))
        gone = sorted(set(manifest()) - set(now_code))
        if gone:
            say("ℹ️ 基线规则下算业务代码、本分支被豁免（不进指纹）：{}{}".format("、".join(gone[:20]), "…" if len(gone) > 20 else ""))
        _, names = git("diff", "--name-only", base, "HEAD", "--", conf().get("specs_dir", "specs"))
        hit = {(ROOT / n).parent.parent.resolve() for n in names.splitlines() if n.endswith("evidence/closed.json")}
        checked = [d for d in all_specs() if is_closed(d) and d in hit]
    for d in all_specs():
        if is_closed(d):
            out += ["{}: {}".format(rel(d), p) for p in spec_problems(d, meta(d))]
    rec = run_tests()                                       # 有基线时用基线的测试命令
    if not rec["ok"]:
        out.append("测试没通过：通过 {} / 失败 {}".format(rec["passed"], rec["failed"]))
    for d in checked:
        c, v = load_json(d / "evidence/closed.json"), load_json(d / "evidence/verify.json") or {}
        say("—— {}".format(rel(d)))
        show(d, meta(d), c.get("manual_tcs") or [])
        if c.get("migrated_from"):
            say("ℹ️ 迁移自 {}，沿用旧评审结论（{}）：没有 0.6 证据，不复核".format(c["migrated_from"], short(c.get("legacy_review"), 120)))
            continue
        if c.get("code_fp") != fp:
            out.append("{}: closed.json 的指纹不是当前代码（关闭后代码又变了，或证据是手写的）".format(rel(d)))
        for tc, o in (v.get("tcs") or {}).items():
            if o == "passed" and rec["tcs"].get(tc) != "passed":
                out.append("{}: verify.json 说 {} 通过，CI 重跑里没有通过的 {}（{}）".format(rel(d), tc, tc, rec["tcs"].get(tc, "报告里没有")))
        if conf().get("review_required", True):
            out += ["{}: {}".format(rel(d), p) for p in review_problems(d, fp)]
    if out:
        fail(out)
    say("ci 通过：测试 {} 个全部通过；复核了 {} 个本分支关闭的 spec".format(rec["passed"], len(checked)))


def main(argv):
    cmds = {"new": cmd_new, "retype": cmd_retype, "check": cmd_check, "verify": cmd_verify, "review": cmd_review, "close": cmd_close,
            "status": cmd_status, "ci": cmd_ci}
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__.strip())
        return
    if argv[0] in ("version", "--version"):
        print(VERSION)
        return
    if argv[0] not in cmds:
        die("未知命令 {}。可用：{}（-h 看用法）".format(argv[0], " / ".join(cmds)))
    cmds[argv[0]](argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
