#!/usr/bin/env python3
"""检查一个 herdr chat 是否真的调用了 Skill(poteto-mode)。

为什么需要它：AGENTS.md 里写「第一步必须调 Skill(poteto-mode)」只是上下文，
模型可以读、可以复述、也可以不执行。唯一可信的证据是它的工具调用序列里
有没有出现 Skill 调用。

**关键坑（2026-11-20 实测踩到）**：`alma herdr read` 返回的是屏幕历史，
新 chat 刚启动时屏幕上还留着上一个 chat 的调用记录。只看「有没有 ⏺ Skill(」
会误判成功。因此必须先用 `❯`（用户输入提示符）切出**最近一次任务**的区域，
只统计该区域内的调用。

用法：
    python3 scripts/check_poteto.py hc:t12
    python3 scripts/check_poteto.py --list                 # 工作区所有 chat
    python3 scripts/check_poteto.py hc:t12 --all-history    # 退化为看全屏（调试用）

退出码：0 = 通过，1 = 未调用，2 = 无法读取该 chat。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# herdr 屏幕输出形如：
#   ⏺ Skill(poteto-mode)
#   ⏺ Bash(cat ...)
#   ⏺ Update(path)
TOOL_RE = re.compile(r"⏺\s+([A-Za-z][A-Za-z0-9_]*)\(([^\n)]*)")
SKILL_RE = re.compile(r"⏺\s+Skill\(([^)\n]*)")

# 用户输入提示符：行首的可选空白 + `❯`。用它切分「每一次任务」。
# 注意：屏幕底部常驻一个**空的**输入框 `❯␣`（\xa0 不换行空格），
# 它不是用户输入，必须排除，否则会把「本轮」切成空段。
PROMPT_RE = re.compile(r"^\s*❯[ \u00a0]*(\S.*)$", re.MULTILINE)

# Claude Code 的结束标记，说明这一轮已经结束。
DONE_RE = re.compile(r"✻\s+.*(?:done|Worked|Brewed|Cooked|Crunched|Drizzling)")


def read_pane(pane: str, lines: int = 6000) -> str:
    proc = subprocess.run(
        ["alma", "herdr", "read", "--pane", pane, "--lines", str(lines)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "alma herdr read failed")
    return proc.stdout


def current_task_segment(screen: str) -> str:
    """截出最近一次用户任务之后的屏幕内容。

    屏幕历史里可能有多个 `❯ ...`（用户历次输入）。取最后一个**带内容**的
    提示符到末尾。底部常驻的空输入框 `❯␣` 不算提示符（见 PROMPT_RE）。
    """
    marks = [m for m in PROMPT_RE.finditer(screen) if m.group(1).strip()]
    if not marks:
        # 没有可识别的用户输入：可能还在启动，或屏幕已滚过这一轮的开头。
        # 返回全屏，由上层用「无调用」报出，不假装通过。
        return screen
    return screen[marks[-1].start():]


def tool_calls(segment: str) -> list[tuple[str, str]]:
    """返回 [(工具名, 参数摘要)]，顺序即调用顺序。"""
    return [(m.group(1), m.group(2).strip()) for m in TOOL_RE.finditer(segment)]


def skill_calls(segment: str) -> list[str]:
    return [m.group(1).strip() for m in SKILL_RE.finditer(segment)]


def check(pane: str, *, all_history: bool = False) -> tuple[bool, str]:
    try:
        screen = read_pane(pane)
    except RuntimeError as exc:
        return False, f"无法读取 {pane}: {exc}"

    if all_history:
        segment = screen
    else:
        marks = [m for m in PROMPT_RE.finditer(screen) if m.group(1).strip()]
        if not marks:
            # 找不到本轮任务的起点 → 无法确认，一律判失败。
            # 宁可误报失败让人复查，也不能误报通过（2026-11-20 踩过这个坑）。
            return False, (
                f"{pane}: 找不到本轮任务的起点（屏幕可能还在启动或已滚动），"
                f"无法确认是否调用 Skill。请加 --all-history 人工核对。"
            )
        segment = screen[marks[-1].start():]

    calls = tool_calls(segment)

    if not calls:
        return False, f"{pane}: 本轮任务还没有工具调用（可能还在启动或已完成）"

    skills = skill_calls(segment)
    ok = any("poteto-mode" in name for name in skills)

    idx = next((i for i, (n, _) in enumerate(calls) if n == "Skill"), None)
    if idx == 0:
        order = "首个工具调用就是 Skill ✅"
    elif idx is None:
        order = "本轮从未调用 Skill ❌"
    else:
        order = f"首个工具调用是 {calls[0][0]}，第 {idx + 1} 个才是 Skill ⚠️"

    counts: dict[str, int] = {}
    for name, _args in calls:
        counts[name] = counts.get(name, 0) + 1
    summary = " / ".join(
        f"{k}×{v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])
    )

    head = "✅" if ok else "❌"
    detail = (
        f"{head} {pane}: poteto-mode {'已调用' if ok else '未调用'}"
        f"｜{order}｜本轮 {len(calls)} 次调用（{summary}）"
    )
    return ok, detail


def list_chats() -> list[str]:
    proc = subprocess.run(
        ["alma", "herdr", "chats", "vigil-workbench"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return re.findall(r"\b(hc:t\d+)\b", proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pane", nargs="?", help="chat pane id，如 hc:t12")
    parser.add_argument(
        "--all-history",
        action="store_true",
        help="退化为看全屏历史（会把上一轮任务的记录算进来，仅调试用）",
    )
    parser.add_argument("--list", action="store_true", help="检查工作区所有 chat")
    args = parser.parse_args()

    if args.list:
        panes = list_chats()
        if not panes:
            print("没有找到任何 chat")
            return 2
        all_ok = True
        for pane in panes:
            ok, detail = check(pane, all_history=args.all_history)
            all_ok = all_ok and ok
            print(detail)
        return 0 if all_ok else 1

    if not args.pane:
        parser.error("需要 pane id，或用 --list")

    ok, detail = check(args.pane, all_history=args.all_history)
    print(detail)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
