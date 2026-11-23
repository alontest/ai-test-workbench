"""`test-case` 两阶段生成、用例库 CRUD、动态 Stale 复核与多格式导出。"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select

from workbench.api.serialization import to_rfc3339
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.models import (
    KnowledgeBase,
    KnowledgeEntry,
    ProjectContext,
    QaSkill,
    TestCase,
    TestCaseDesignPlan,
)
from workbench.services import calls as calls_service
from workbench.services import sessions as sessions_service
from workbench.services import skills as skills_service
from workbench.services.ai_gateway import AiGateway
from workbench.services.errors import DomainError

PRIORITIES = ("P0", "P1", "P2", "P3")
CASE_TYPES = ("functional", "boundary", "exception", "security", "concurrency")
EXPORT_FORMATS = ("csv", "markdown", "json")
MAX_CHECKPOINTS = 30

_JSON_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.DOTALL)


# ---------------------------------------------------------------------------
# 通用校验与清洗
# ---------------------------------------------------------------------------


def _clean_required(value: str | None, *, field: str, max_len: int | None = None) -> str:
    cleaned = (value or "").strip()
    if not cleaned:
        raise DomainError(
            "validation_error",
            f"{field} 不能为空。",
            details=[{"field": field, "message": "不能为空"}],
        )
    if max_len is not None and len(cleaned) > max_len:
        raise DomainError(
            "validation_error",
            f"{field} 长度不能超过 {max_len} 个字符。",
            details=[{"field": field, "message": f"长度上限 {max_len}"}],
        )
    return cleaned


def _clean_optional(value: str | None, *, field: str, max_len: int) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) > max_len:
        raise DomainError(
            "validation_error",
            f"{field} 长度不能超过 {max_len} 个字符。",
            details=[{"field": field, "message": f"长度上限 {max_len}"}],
        )
    return cleaned


def _clip(value: str | None, max_len: int) -> str:
    """模型输出属外部输入：超长截断而不是整单失败。"""
    return (value or "").strip()[:max_len]


def _as_bool(value: Any, *, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() not in ("false", "0", "no", "off")
    if value is None:
        return default
    return bool(value)


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value).strip()
    return [cleaned] if cleaned else []


def _dedupe(values: Sequence[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def _clean_priority(value: Any, *, fallback: str = "P1") -> str:
    cleaned = str(value or "").strip().upper()
    return cleaned if cleaned in PRIORITIES else fallback


def _clean_case_type(value: Any, *, fallback: str = "functional") -> str:
    cleaned = str(value or "").strip().lower()
    return cleaned if cleaned in CASE_TYPES else fallback


def _normalize_steps(raw: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index, item in enumerate(raw or ()):
        if isinstance(item, Mapping):
            action = str(item.get("action") or item.get("step") or "").strip()
            expected = str(
                item.get("expected") or item.get("expectedResult") or ""
            ).strip()
            try:
                step_no = int(item.get("stepNo", item.get("step_no", index + 1)))
            except (TypeError, ValueError):
                step_no = index + 1
            if action or expected:
                steps.append({"stepNo": step_no, "action": action, "expected": expected})
        elif isinstance(item, str) and item.strip():
            steps.append({"stepNo": index + 1, "action": item.strip(), "expected": ""})
    if not steps:
        steps = [
            {
                "stepNo": 1,
                "action": "执行检查点对应的业务操作",
                "expected": "系统行为符合检查点预期",
            }
        ]
    return steps


def _normalize_kb_links(value: Any) -> list[dict[str, str]]:
    links: list[dict[str, str]] = []
    for item in value or ():
        if not isinstance(item, Mapping):
            raise DomainError(
                "validation_error",
                "知识锚点必须是对象数组。",
                details=[{"field": "kbLinks", "message": "invalid anchor"}],
            )
        code = str(item.get("code") or "").strip()
        if not code:
            raise DomainError(
                "validation_error",
                "知识锚点缺少条目编号。",
                details=[{"field": "kbLinks", "message": "code required"}],
            )
        links.append(
            {
                "kbId": str(item.get("kbId") or ""),
                "kbNameKey": str(item.get("kbNameKey") or ""),
                "code": code,
                "codeKey": str(item.get("codeKey") or code.casefold()),
                "title": str(item.get("title") or ""),
                "contentDigest": str(item.get("contentDigest") or ""),
            }
        )
    return links


def _kb_link_snapshot(kb: KnowledgeBase, entry: KnowledgeEntry) -> dict[str, str]:
    return {
        "kbId": kb.kb_id,
        "kbNameKey": kb.name_key,
        "code": entry.code,
        "codeKey": entry.code_key,
        "title": entry.title,
        "contentDigest": entry.content_digest,
    }


# ---------------------------------------------------------------------------
# 知识锚点与技能解析
# ---------------------------------------------------------------------------


async def _load_kb_refs(
    db, project_id: int, kb_refs: Sequence[Mapping[str, Any]] | None  # noqa: ANN001
) -> list[dict[str, str]]:
    snapshots: list[dict[str, str]] = []
    for ref in kb_refs or ():
        kb_id = str(ref.get("kbId") or "").strip()
        kb = await db.get(KnowledgeBase, kb_id) if kb_id else None
        if kb is None or kb.project_id != project_id:
            raise DomainError(
                "knowledge_not_found",
                "知识库不存在或不属于该项目。",
                status_code=404,
                details=[{"field": "kbRefs", "message": f"kb {kb_id} not found"}],
            )
        codes = [code.casefold() for code in _as_str_list(ref.get("entryCodes"))]
        stmt = select(KnowledgeEntry).where(KnowledgeEntry.kb_id == kb_id)
        if codes:
            stmt = stmt.where(KnowledgeEntry.code_key.in_(codes))
        entries = list(await db.scalars(stmt))
        if codes:
            found = {entry.code_key.casefold() for entry in entries}
            missing = [code for code in codes if code not in found]
            if missing:
                raise DomainError(
                    "knowledge_entry_not_found",
                    "知识条目不存在。",
                    status_code=404,
                    details=[
                        {"field": "entryCodes", "message": ", ".join(missing)}
                    ],
                )
        snapshots.extend(_kb_link_snapshot(kb, entry) for entry in entries)
    return snapshots


async def _resolve_skill(
    db, project_id: int, skill_id: str | None  # noqa: ANN001
) -> QaSkill:
    if not skill_id:
        return await skills_service.ensure_builtin_skills(db)
    skill = await db.get(QaSkill, skill_id)
    if skill is None:
        raise DomainError(
            "skill_not_found",
            "QA 技能不存在。",
            status_code=404,
            details=[{"field": "skillId", "message": "skill not found"}],
        )
    if skill.scope == "project" and skill.project_id != project_id:
        raise DomainError(
            "validation_error",
            "该项目不能使用其他项目的专属技能。",
            details=[{"field": "skillId", "message": "scope not allowed"}],
        )
    return skill


# ---------------------------------------------------------------------------
# 模型输出解析
# ---------------------------------------------------------------------------


def _extract_json(raw: str | None) -> Any | None:
    text = (raw or "").strip()
    if not text:
        return None
    candidates: list[str] = [match.group(1).strip() for match in _JSON_FENCE_RE.finditer(text)]
    candidates.append(text)
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            candidates.append(text[start : end + 1])
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except (TypeError, ValueError):
            continue
    return None


def _coerce_dict_list(payload: Any, keys: Sequence[str]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, Mapping)]
    if isinstance(payload, Mapping):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, Mapping)]
            if isinstance(value, Mapping):
                return [dict(value)]
        if any(key in payload for key in ("checkpointId", "scenario", "title", "steps")):
            return [dict(payload)]
    return []


def _normalize_checkpoint(
    item: Mapping[str, Any],
    index: int,
    *,
    default_module: str,
    default_kb_codes: Sequence[str] = (),
    default_code_paths: Sequence[str] = (),
) -> dict[str, Any]:
    checkpoint_id = _clip(
        str(item.get("checkpointId") or item.get("id") or ""), 64
    )
    kb_codes = _as_str_list(item.get("kbCodes") or item.get("kb_codes"))
    code_paths = _as_str_list(item.get("codePaths") or item.get("code_paths"))
    return {
        "checkpointId": checkpoint_id or f"CP-{index:02d}",
        "module": _clip(str(item.get("module") or ""), 120)
        or _clip(default_module, 120)
        or "未分类",
        "scenario": _clip(
            str(
                item.get("scenario")
                or item.get("description")
                or item.get("title")
                or ""
            ),
            500,
        ),
        "category": _clean_case_type(item.get("category")),
        "priority": _clean_priority(item.get("priority")),
        "rationale": _clip(str(item.get("rationale") or item.get("reason") or ""), 1000),
        "kbCodes": kb_codes or list(default_kb_codes),
        "codePaths": code_paths or list(default_code_paths),
        "selected": _as_bool(item.get("selected"), default=True),
    }


def _fallback_checkpoints(
    *,
    title: str,
    requirement_text: str,
    kb_codes: Sequence[str],
    code_paths: Sequence[str],
) -> list[dict[str, Any]]:
    lines = [
        line.strip(" \t-#*")
        for line in requirement_text.splitlines()
        if line.strip(" \t-#*")
    ][:MAX_CHECKPOINTS]
    scenarios = lines or [title]
    return [
        {
            "checkpointId": f"CP-{index:02d}",
            "module": title[:120],
            "scenario": scenario[:500],
            "category": "functional",
            "priority": "P1",
            "rationale": "模型输出无法解析，按需求正文生成确定性兜底检查点。",
            "kbCodes": list(kb_codes),
            "codePaths": list(code_paths),
            "selected": True,
        }
        for index, scenario in enumerate(scenarios, start=1)
    ]


def _parse_checkpoints(
    raw: str | None,
    *,
    title: str,
    requirement_text: str,
    kb_links: Sequence[Mapping[str, str]],
    code_paths: Sequence[str],
) -> list[dict[str, Any]]:
    items = _coerce_dict_list(_extract_json(raw), ("checkpoints", "items", "data"))
    kb_codes = [link["code"] for link in kb_links]
    if not items:
        return _fallback_checkpoints(
            title=title,
            requirement_text=requirement_text,
            kb_codes=kb_codes,
            code_paths=code_paths,
        )
    checkpoints: list[dict[str, Any]] = []
    for index, item in enumerate(items[:MAX_CHECKPOINTS], start=1):
        checkpoints.append(
            _normalize_checkpoint(
                item,
                index,
                default_module=title,
                default_kb_codes=kb_codes,
                default_code_paths=code_paths,
            )
        )
    return checkpoints


def _normalize_case(
    item: Mapping[str, Any],
    checkpoint: Mapping[str, Any],
    *,
    default_case_code: str,
) -> dict[str, Any]:
    kb_codes = _as_str_list(item.get("kbCodes") or item.get("kb_codes"))
    code_paths = _as_str_list(item.get("codePaths") or item.get("code_paths"))
    return {
        "checkpointId": str(item.get("checkpointId") or checkpoint["checkpointId"]),
        "caseCode": _clip(
            str(
                item.get("caseCode")
                or item.get("case_code")
                or item.get("code")
                or default_case_code
            ),
            64,
        )
        or default_case_code,
        "module": _clip(str(item.get("module") or ""), 120)
        or str(checkpoint.get("module") or "未分类"),
        "title": _clip(str(item.get("title") or ""), 300)
        or _clip(str(checkpoint.get("scenario") or ""), 300)
        or "未命名用例",
        "priority": _clean_priority(
            item.get("priority"), fallback=_clean_priority(checkpoint.get("priority"))
        ),
        "caseType": _clean_case_type(
            item.get("caseType") or item.get("case_type"),
            fallback=_clean_case_type(checkpoint.get("category")),
        ),
        "preconditions": _as_str_list(
            item.get("preconditions") or item.get("precondition")
        ),
        "steps": _normalize_steps(item.get("steps")),
        "expectedSummary": _clip(
            str(
                item.get("expectedSummary")
                or item.get("expected_summary")
                or item.get("expected")
                or checkpoint.get("rationale")
                or checkpoint.get("scenario")
                or ""
            ),
            4000,
        )
        or "行为符合检查点预期",
        "kbCodes": kb_codes or list(checkpoint.get("kbCodes") or []),
        "codePaths": code_paths or list(checkpoint.get("codePaths") or []),
    }


def _fallback_cases(
    selected: Sequence[Mapping[str, Any]], *, first_case_seq: int
) -> list[dict[str, Any]]:
    return [
        {
            "checkpointId": checkpoint["checkpointId"],
            "caseCode": f"TC-{first_case_seq + index:03d}",
            "module": checkpoint.get("module") or "未分类",
            "title": (checkpoint.get("scenario") or "未命名检查点")[:300],
            "priority": _clean_priority(checkpoint.get("priority")),
            "caseType": _clean_case_type(checkpoint.get("category")),
            "preconditions": [],
            "steps": _normalize_steps([]),
            "expectedSummary": checkpoint.get("rationale")
            or checkpoint.get("scenario")
            or "行为符合检查点预期",
            "kbCodes": list(checkpoint.get("kbCodes") or []),
            "codePaths": list(checkpoint.get("codePaths") or []),
        }
        for index, checkpoint in enumerate(selected)
    ]


# ---------------------------------------------------------------------------
# 提示词
# ---------------------------------------------------------------------------


def _kb_lines(kb_links: Sequence[Mapping[str, str]]) -> str:
    if not kb_links:
        return "（未注入知识条目）"
    return "\n".join(
        f"- [{link['code']}] {link['title']}（知识库 {link['kbNameKey']}）"
        for link in kb_links
    )


def _path_lines(code_paths: Sequence[str]) -> str:
    return "\n".join(f"- {path}" for path in code_paths) or "（未指定代码路径）"


def _build_plan_prompt(
    *,
    skill_content: str,
    skill_version: int,
    title: str,
    requirement_text: str,
    kb_links: Sequence[Mapping[str, str]],
    code_paths: Sequence[str],
) -> str:
    return (
        f"你正在执行【阶段 1：测试设计检查点矩阵】。\n"
        f"请严格遵循下面的 QA 技能规范（v{skill_version}）：\n"
        f"{skill_content}\n\n"
        f"【测试设计主题】{title}\n"
        f"【需求/变更正文】\n{requirement_text}\n\n"
        f"【注入的知识条目】\n{_kb_lines(kb_links)}\n\n"
        f"【关联代码路径】\n{_path_lines(code_paths)}\n\n"
        "只输出 JSON 对象，格式为 "
        '{"checkpoints": [{"checkpointId", "module", "scenario", "category", '
        '"priority", "rationale", "kbCodes", "codePaths", "selected"}]}。'
        "category 取 functional|boundary|exception|security|concurrency，"
        "priority 取 P0|P1|P2|P3。不要输出 JSON 以外的内容。"
    )


def _build_case_prompt(
    *,
    skill_content: str | None,
    skill_version: int | None,
    title: str,
    requirement_text: str,
    selected: Sequence[Mapping[str, Any]],
    kb_links: Sequence[Mapping[str, str]],
    code_paths: Sequence[str],
) -> str:
    skill_block = (
        f"请严格遵循 QA 技能规范（v{skill_version}）：\n{skill_content}\n\n"
        if skill_content
        else ""
    )
    checkpoint_json = json.dumps(list(selected), ensure_ascii=False, indent=2)
    return (
        f"你正在执行【阶段 2：结构化测试用例生成】。\n"
        f"{skill_block}"
        f"【测试设计主题】{title}\n"
        f"【需求/变更正文】\n{requirement_text}\n\n"
        f"【注入的知识条目】\n{_kb_lines(kb_links)}\n\n"
        f"【关联代码路径】\n{_path_lines(code_paths)}\n\n"
        f"【已勾选检查点】\n{checkpoint_json}\n\n"
        "只为上述勾选检查点生成可直接执行的测试用例，输出 JSON 对象 "
        '{"cases": [{"checkpointId", "caseCode", "module", "title", "priority", '
        '"caseType", "preconditions", "steps": [{"stepNo", "action", "expected"}], '
        '"expectedSummary", "kbCodes", "codePaths"}]}。'
        "priority 取 P0|P1|P2|P3，caseType 取 "
        "functional|boundary|exception|security|concurrency。不要编造未出现的知识编号或代码路径。"
    )


# ---------------------------------------------------------------------------
# 阶段 1
# ---------------------------------------------------------------------------


def serialize_plan(row: TestCaseDesignPlan) -> dict[str, Any]:
    return {
        "planId": row.plan_id,
        "projectId": row.project_id,
        "sessionId": row.session_id,
        "callId": row.call_id,
        "skillId": row.skill_id,
        "skillVersion": row.skill_version,
        "title": row.title,
        "requirementText": row.requirement_text,
        "checkpoints": list(row.checkpoints or []),
        "kbLinks": list(row.kb_links or []),
        "codePaths": list(row.code_paths or []),
        "status": row.status,
        "createdAt": to_rfc3339(row.created_at),
        "updatedAt": to_rfc3339(row.updated_at),
    }


async def create_plan(
    project_id: int,
    *,
    model_id: int | None,
    title: str,
    requirement_text: str,
    session_id: int | None = None,
    skill_id: str | None = None,
    kb_refs: Sequence[Mapping[str, Any]] | None = None,
    code_paths: Sequence[str] | None = None,
    gateway: AiGateway | None = None,
) -> dict[str, Any]:
    if model_id is None:
        raise DomainError(
            "validation_error",
            "阶段 1 需要指定 modelId。",
            details=[{"field": "modelId", "message": "required"}],
        )
    cleaned_title = _clean_required(title, field="title", max_len=200)
    cleaned_requirement = _clean_required(requirement_text, field="requirementText")
    cleaned_paths = _dedupe(_as_str_list(code_paths))

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        project = await db.get(ProjectContext, project_id)
        if project is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "project not found"}],
            )
        skill = await _resolve_skill(db, project_id, skill_id)
        kb_links = await _load_kb_refs(db, project_id, kb_refs)
        resolved_skill_id = skill.skill_id
        skill_version = int(skill.current_version)
        skill_content = skill.content_md

    if session_id is None:
        created = await sessions_service.create(
            project_id=project_id,
            entrance_key="case-library",
            title=cleaned_title,
            model_id=model_id,
        )
        resolved_session_id = created["session_id"]
        await sessions_service.append_event(
            resolved_session_id,
            "input_text",
            {
                "title": cleaned_title,
                "text": cleaned_requirement,
                "charCount": len(cleaned_requirement),
            },
        )
    else:
        detail = await sessions_service.get_session(session_id)
        if detail["project"]["projectId"] != project_id:
            raise DomainError(
                "validation_error",
                "会话不属于该项目。",
                details=[{"field": "sessionId", "message": "project mismatch"}],
            )
        resolved_session_id = session_id

    prompt = _build_plan_prompt(
        skill_content=skill_content,
        skill_version=skill_version,
        title=cleaned_title,
        requirement_text=cleaned_requirement,
        kb_links=kb_links,
        code_paths=cleaned_paths,
    )
    call_result = await calls_service.complete(
        resolved_session_id,
        prompt=prompt,
        gateway=gateway,
    )
    checkpoints = _parse_checkpoints(
        str(call_result.get("resultText") or ""),
        title=cleaned_title,
        requirement_text=cleaned_requirement,
        kb_links=kb_links,
        code_paths=cleaned_paths,
    )

    now = utcnow()
    async with sessionmaker() as db:
        row = TestCaseDesignPlan(
            plan_id=uuid4().hex,
            project_id=project_id,
            session_id=resolved_session_id,
            call_id=call_result["callId"],
            skill_id=resolved_skill_id,
            skill_version=skill_version,
            title=cleaned_title,
            requirement_text=cleaned_requirement,
            checkpoints=checkpoints,
            kb_links=kb_links,
            code_paths=cleaned_paths,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return serialize_plan(row)


async def get_plan(plan_id: str) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(TestCaseDesignPlan, plan_id)
        if row is None:
            raise DomainError(
                "plan_not_found",
                "测试设计计划不存在。",
                status_code=404,
                details=[{"field": "planId", "message": "plan not found"}],
            )
        return serialize_plan(row)


async def list_plans(project_id: int) -> list[dict[str, Any]]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        project = await db.get(ProjectContext, project_id)
        if project is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "project not found"}],
            )
        rows = list(
            await db.scalars(
                select(TestCaseDesignPlan)
                .where(TestCaseDesignPlan.project_id == project_id)
                .order_by(
                    TestCaseDesignPlan.created_at.desc(),
                    TestCaseDesignPlan.plan_id.desc(),
                )
            )
        )
        return [serialize_plan(row) for row in rows]


# ---------------------------------------------------------------------------
# 阶段 2
# ---------------------------------------------------------------------------


async def generate_cases(
    plan_id: str,
    *,
    selected_checkpoint_ids: Sequence[str],
    checkpoints_override: Sequence[Mapping[str, Any]] | None = None,
    model_id: int | None = None,  # noqa: ARG001 - 模型由所属会话决定
    gateway: AiGateway | None = None,
) -> dict[str, Any]:
    selected_ids = {str(item).strip() for item in selected_checkpoint_ids if str(item).strip()}
    if not selected_ids:
        raise DomainError(
            "no_checkpoints_selected",
            "请至少勾选一个检查点后再生成用例。",
            details=[{"field": "selectedCheckpointIds", "message": "at least one required"}],
        )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        plan = await db.get(TestCaseDesignPlan, plan_id)
        if plan is None:
            raise DomainError(
                "plan_not_found",
                "测试设计计划不存在。",
                status_code=404,
                details=[{"field": "planId", "message": "plan not found"}],
            )
        plan_title = plan.title
        plan_requirement = plan.requirement_text
        plan_session_id = plan.session_id
        plan_skill_id = plan.skill_id
        plan_kb_links = list(plan.kb_links or [])
        plan_code_paths = list(plan.code_paths or [])
        if checkpoints_override:
            normalized_override = [
                _normalize_checkpoint(
                    item,
                    index,
                    default_module=plan_title,
                    default_kb_codes=[link["code"] for link in plan_kb_links],
                    default_code_paths=plan_code_paths,
                )
                for index, item in enumerate(checkpoints_override, start=1)
            ]
        else:
            normalized_override = None
        checkpoints = normalized_override if normalized_override is not None else list(
            plan.checkpoints or []
        )
        selected = [
            checkpoint
            for checkpoint in checkpoints
            if str(checkpoint.get("checkpointId")) in selected_ids
        ]
        if not selected:
            raise DomainError(
                "no_checkpoints_selected",
                "勾选的检查点不存在或已失效。",
                details=[{"field": "selectedCheckpointIds", "message": "no matching checkpoint"}],
            )
        project_id = plan.project_id
        skill = await db.get(QaSkill, plan_skill_id) if plan_skill_id else None
        skill_content = skill.content_md if skill is not None else None
        skill_version = int(skill.current_version) if skill is not None else None
        existing_count = int(
            await db.scalar(
                select(func.count())
                .select_from(TestCase)
                .where(TestCase.project_id == project_id)
            )
            or 0
        )

    prompt = _build_case_prompt(
        skill_content=skill_content,
        skill_version=skill_version,
        title=plan_title,
        requirement_text=plan_requirement,
        selected=selected,
        kb_links=plan_kb_links,
        code_paths=plan_code_paths,
    )
    call_result = await calls_service.complete(
        plan_session_id,
        prompt=prompt,
        gateway=gateway,
    )

    parsed = _coerce_dict_list(_extract_json(str(call_result.get("resultText") or "")), ("cases",))
    checkpoint_by_id = {
        str(checkpoint.get("checkpointId")): checkpoint for checkpoint in selected
    }
    normalized_cases: list[tuple[dict[str, Any], Mapping[str, Any]]] = []
    if parsed:
        for index, item in enumerate(parsed):
            checkpoint = checkpoint_by_id.get(str(item.get("checkpointId")))
            if checkpoint is None:
                checkpoint = selected[min(index, len(selected) - 1)]
            normalized_cases.append(
                (
                    _normalize_case(
                        item,
                        checkpoint,
                        default_case_code=f"TC-{existing_count + index + 1:03d}",
                    ),
                    checkpoint,
                )
            )
    else:
        for index, item in enumerate(
            _fallback_cases(selected, first_case_seq=existing_count + 1)
        ):
            normalized_cases.append((item, selected[min(index, len(selected) - 1)]))

    now = utcnow()
    async with sessionmaker() as db:
        plan = await db.get(TestCaseDesignPlan, plan_id)
        if plan is None:
            raise DomainError(
                "plan_not_found",
                "测试设计计划不存在。",
                status_code=404,
                details=[{"field": "planId", "message": "plan not found"}],
            )
        if normalized_override is not None:
            plan.checkpoints = normalized_override
        plan.status = "generated"
        plan.updated_at = now

        stale_index = await _load_stale_index(db, project_id)
        snapshots = [_kb_link_snapshot_map(link) for link in plan_kb_links]
        rows: list[TestCase] = []
        for case, checkpoint in normalized_cases:
            links = _bind_links(
                case.get("kbCodes") or [],
                snapshots,
            )
            paths = _dedupe(
                _as_str_list(case.get("codePaths")) or list(plan_code_paths)
            )
            row = TestCase(
                case_id=uuid4().hex,
                project_id=project_id,
                plan_id=plan_id,
                checkpoint_id=str(checkpoint.get("checkpointId")),
                session_id=plan_session_id,
                call_id=call_result["callId"],
                skill_id=plan_skill_id,
                skill_version=plan.skill_version,
                case_code=case["caseCode"],
                module=case["module"] or "未分类",
                title=case["title"],
                priority=case["priority"],
                case_type=case["caseType"],
                preconditions=case["preconditions"],
                steps=case["steps"],
                expected_summary=case["expectedSummary"],
                kb_links=links,
                code_paths=paths,
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            rows.append(row)
        items = [
            serialize_test_case(row, _compute_stale(row.kb_links, stale_index))
            for row in rows
        ]
        await db.commit()
        return {
            "planId": plan_id,
            "sessionId": plan_session_id,
            "callId": call_result["callId"],
            "generatedCount": len(items),
            "items": items,
        }


def _kb_link_snapshot_map(link: Mapping[str, Any]) -> dict[str, str]:
    return {
        "kbId": str(link.get("kbId") or ""),
        "kbNameKey": str(link.get("kbNameKey") or ""),
        "code": str(link.get("code") or ""),
        "codeKey": str(link.get("codeKey") or str(link.get("code") or "").casefold()),
        "title": str(link.get("title") or ""),
        "contentDigest": str(link.get("contentDigest") or ""),
    }


def _bind_links(
    case_kb_codes: Sequence[str], plan_links: Sequence[Mapping[str, str]]
) -> list[dict[str, str]]:
    if case_kb_codes:
        wanted = {str(code).casefold() for code in case_kb_codes}
        matched = [
            _kb_link_snapshot_map(link)
            for link in plan_links
            if str(link.get("code") or "").casefold() in wanted
        ]
        if matched:
            return matched
    return [_kb_link_snapshot_map(link) for link in plan_links]


# ---------------------------------------------------------------------------
# Stale 动态计算
# ---------------------------------------------------------------------------


async def _load_stale_index(db, project_id: int) -> dict[str, dict[str, Any]]:  # noqa: ANN001
    kbs = list(
        await db.scalars(
            select(KnowledgeBase).where(
                KnowledgeBase.project_id == project_id,
                KnowledgeBase.current_flag == "1",
            )
        )
    )
    kb_by_id = {kb.kb_id: kb for kb in kbs}
    code_maps: dict[str, dict[str, KnowledgeEntry]] = {kb.kb_id: {} for kb in kbs}
    if kb_by_id:
        entries = list(
            await db.scalars(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.kb_id.in_(list(kb_by_id))
                )
            )
        )
        for entry in entries:
            code_maps[entry.kb_id][str(entry.code_key).casefold()] = entry
            code_maps[entry.kb_id].setdefault(str(entry.code).casefold(), entry)
    return {
        kb.name_key.casefold(): {"kb": kb, "entries": code_maps[kb.kb_id]}
        for kb in kbs
    }


def _compute_stale(
    kb_links: Sequence[Mapping[str, Any]] | None,
    index: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []
    details: list[dict[str, str]] = []
    for link in kb_links or ():
        kb_name_key = str(link.get("kbNameKey") or "").casefold()
        code_key = str(link.get("codeKey") or link.get("code") or "").casefold()
        node = index.get(kb_name_key)
        if node is None:
            reason = "kb_deleted"
            message = f"知识库 {link.get('kbNameKey') or ''} 已不存在或不再生效。"
        else:
            entry = node["entries"].get(code_key)
            if entry is None:
                reason = "entry_removed"
                message = f"知识条目 {link.get('code') or code_key} 已从当前知识库移除。"
            elif str(entry.content_digest) != str(link.get("contentDigest") or ""):
                reason = "entry_modified"
                message = f"知识条目 {link.get('code') or code_key} 的内容已更新。"
            else:
                continue
        details.append(
            {
                "code": str(link.get("code") or ""),
                "kbNameKey": str(link.get("kbNameKey") or ""),
                "reason": reason,
                "message": message,
            }
        )
        if reason not in reasons:
            reasons.append(reason)
    return {
        "status": "stale" if reasons else "fresh",
        "reasons": reasons,
        "details": details,
    }


def serialize_test_case(
    row: TestCase, stale: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    computed = dict(stale or {"status": "fresh", "reasons": [], "details": []})
    return {
        "caseId": row.case_id,
        "projectId": row.project_id,
        "planId": row.plan_id,
        "checkpointId": row.checkpoint_id,
        "sessionId": row.session_id,
        "callId": row.call_id,
        "skillId": row.skill_id,
        "skillVersion": row.skill_version,
        "caseCode": row.case_code,
        "module": row.module,
        "title": row.title,
        "priority": row.priority,
        "caseType": row.case_type,
        "preconditions": list(row.preconditions or []),
        "steps": list(row.steps or []),
        "expectedSummary": row.expected_summary,
        "kbLinks": [_kb_link_snapshot_map(link) for link in row.kb_links or ()],
        "codePaths": list(row.code_paths or []),
        "staleStatus": computed["status"],
        "staleReasons": list(computed["reasons"]),
        "staleDetails": list(computed["details"]),
        "createdAt": to_rfc3339(row.created_at),
        "updatedAt": to_rfc3339(row.updated_at),
    }


# ---------------------------------------------------------------------------
# 用例库查询、编辑、删除与复核
# ---------------------------------------------------------------------------


def _like_prefix(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"{escaped}%"


def _like_contains(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _module_tree(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    roots: dict[str, dict[str, Any]] = {}

    def node_for(level: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
        node = level.get(name)
        if node is None:
            node = {"name": name, "count": 0, "children": {}}
            level[name] = node
        return node

    for item in items:
        parts = [
            part.strip()
            for part in str(item.get("module") or "").split("/")
            if part.strip()
        ] or ["未分类"]
        level = roots
        for part in parts:
            node = node_for(level, part)
            node["count"] += 1
            level = node["children"]

    def render(level: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "name": name,
                "count": level[name]["count"],
                "children": render(level[name]["children"]),
            }
            for name in sorted(level)
        ]

    return render(roots)


def _summarize(items: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_priority = {priority: 0 for priority in PRIORITIES}
    stale_count = 0
    for item in items:
        priority = str(item.get("priority") or "P1")
        by_priority[priority] = by_priority.get(priority, 0) + 1
        if item.get("staleStatus") == "stale":
            stale_count += 1
    total = len(items)
    return {
        "totalCount": total,
        "staleCount": stale_count,
        "freshCount": total - stale_count,
        "byPriority": by_priority,
        "moduleTree": _module_tree(items),
    }


async def list_test_cases(
    project_id: int,
    *,
    module: str | None = None,
    priority: str | None = None,
    stale_only: bool = False,
    q: str | None = None,
) -> dict[str, Any]:
    if priority is not None and priority.upper() not in PRIORITIES:
        raise DomainError(
            "validation_error",
            "优先级过滤值必须为 P0–P3。",
            details=[{"field": "priority", "message": f"invalid priority {priority}"}],
        )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        project = await db.get(ProjectContext, project_id)
        if project is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "project not found"}],
            )
        stmt = select(TestCase).where(TestCase.project_id == project_id)
        if module:
            stmt = stmt.where(
                TestCase.module.like(_like_prefix(module.strip()), escape="\\")
            )
        if priority is not None:
            stmt = stmt.where(TestCase.priority == priority.upper())
        if q:
            pattern = _like_contains(q.strip())
            stmt = stmt.where(
                TestCase.title.like(pattern, escape="\\")
                | TestCase.case_code.like(pattern, escape="\\")
            )
        stmt = stmt.order_by(TestCase.created_at.desc(), TestCase.case_id.desc())
        rows = list(await db.scalars(stmt))
        index = await _load_stale_index(db, project_id)
        items = [
            serialize_test_case(row, _compute_stale(row.kb_links, index))
            for row in rows
        ]
    if stale_only:
        items = [item for item in items if item["staleStatus"] == "stale"]
    return {"items": items, "summary": _summarize(items)}


async def get_test_case(case_id: str) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(TestCase, case_id)
        if row is None:
            raise _case_not_found()
        index = await _load_stale_index(db, row.project_id)
        return serialize_test_case(row, _compute_stale(row.kb_links, index))


def _case_not_found() -> DomainError:
    return DomainError(
        "test_case_not_found",
        "测试用例不存在。",
        status_code=404,
        details=[{"field": "caseId", "message": "case not found"}],
    )


async def update_test_case(
    case_id: str,
    *,
    title: str | None = None,
    module: str | None = None,
    priority: str | None = None,
    case_type: str | None = None,
    preconditions: Sequence[str] | None = None,
    steps: Sequence[Mapping[str, Any]] | None = None,
    expected_summary: str | None = None,
    kb_links: Sequence[Mapping[str, Any]] | None = None,
    code_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    if priority is not None and priority.strip().upper() not in PRIORITIES:
        raise DomainError(
            "validation_error",
            "优先级必须为 P0–P3。",
            details=[{"field": "priority", "message": "invalid priority"}],
        )
    if case_type is not None and case_type.strip().lower() not in CASE_TYPES:
        raise DomainError(
            "validation_error",
            "用例类型非法。",
            details=[{"field": "caseType", "message": "invalid case type"}],
        )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(TestCase, case_id)
        if row is None:
            raise _case_not_found()
        if title is not None:
            row.title = _clean_required(title, field="title", max_len=300)
        if module is not None:
            row.module = _clean_optional(module, field="module", max_len=120) or row.module
        if priority is not None:
            row.priority = _clean_priority(priority)
        if case_type is not None:
            row.case_type = _clean_case_type(case_type)
        if preconditions is not None:
            row.preconditions = _as_str_list(preconditions)
        if steps is not None:
            row.steps = _normalize_steps(steps)
        if expected_summary is not None:
            row.expected_summary = _clean_required(
                expected_summary, field="expectedSummary"
            )
        if kb_links is not None:
            row.kb_links = _normalize_kb_links(kb_links)
        if code_paths is not None:
            row.code_paths = _dedupe(_as_str_list(code_paths))
        row.updated_at = utcnow()
        await db.commit()
        await db.refresh(row)
        index = await _load_stale_index(db, row.project_id)
        return serialize_test_case(row, _compute_stale(row.kb_links, index))


async def delete_test_case(case_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(TestCase, case_id)
        if row is None:
            raise _case_not_found()
        await db.delete(row)
        await db.commit()


async def acknowledge_stale(case_id: str) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(TestCase, case_id)
        if row is None:
            raise _case_not_found()
        index = await _load_stale_index(db, row.project_id)
        refreshed: list[dict[str, str]] = []
        for link in row.kb_links or ():
            node = index.get(str(link.get("kbNameKey") or "").casefold())
            if node is None:
                continue
            entry = node["entries"].get(
                str(link.get("codeKey") or link.get("code") or "").casefold()
            )
            if entry is None:
                continue
            refreshed.append(_kb_link_snapshot(node["kb"], entry))
        row.kb_links = refreshed
        row.updated_at = utcnow()
        await db.commit()
        await db.refresh(row)
        return serialize_test_case(row, _compute_stale(refreshed, index))


# ---------------------------------------------------------------------------
# 多格式导出
# ---------------------------------------------------------------------------


def _step_text(steps: Sequence[Mapping[str, Any]]) -> str:
    return " | ".join(
        f"{step.get('stepNo')}. {step.get('action')} -> {step.get('expected')}"
        for step in steps
    )


def _export_row(item: Mapping[str, Any]) -> dict[str, str]:
    return {
        "caseCode": str(item.get("caseCode") or ""),
        "module": str(item.get("module") or ""),
        "title": str(item.get("title") or ""),
        "priority": str(item.get("priority") or ""),
        "caseType": str(item.get("caseType") or ""),
        "preconditions": " | ".join(item.get("preconditions") or []),
        "steps": _step_text(item.get("steps") or []),
        "expectedSummary": str(item.get("expectedSummary") or ""),
        "kbCodes": ", ".join(
            str(link.get("code") or "") for link in item.get("kbLinks") or []
        ),
        "codePaths": ", ".join(item.get("codePaths") or []),
        "staleStatus": str(item.get("staleStatus") or "fresh"),
        "staleReasons": ", ".join(item.get("staleReasons") or []),
    }


def _render_csv(items: Sequence[Mapping[str, Any]]) -> str:
    buffer = io.StringIO()
    columns = list(_export_row(items[0]).keys()) if items else [
        "caseCode",
        "module",
        "title",
        "priority",
        "caseType",
        "preconditions",
        "steps",
        "expectedSummary",
        "kbCodes",
        "codePaths",
        "staleStatus",
        "staleReasons",
    ]
    writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    for item in items:
        writer.writerow(_export_row(item))
    return buffer.getvalue()


def _escape_markdown(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _render_markdown(items: Sequence[Mapping[str, Any]]) -> str:
    headers = [
        "编号",
        "模块",
        "标题",
        "优先级",
        "类型",
        "前置条件",
        "步骤",
        "预期结果",
        "知识锚点",
        "代码路径",
        "复核状态",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for item in items:
        row = _export_row(item)
        values = [
            row["caseCode"],
            row["module"],
            row["title"],
            row["priority"],
            row["caseType"],
            row["preconditions"],
            row["steps"],
            row["expectedSummary"],
            row["kbCodes"],
            row["codePaths"],
            row["staleStatus"],
        ]
        lines.append("| " + " | ".join(_escape_markdown(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


async def export_test_cases(
    project_id: int, *, format: str  # noqa: A002
) -> dict[str, Any]:
    cleaned_format = (format or "").strip().lower()
    if cleaned_format not in EXPORT_FORMATS:
        raise DomainError(
            "validation_error",
            "导出格式必须为 csv、markdown 或 json。",
            details=[{"field": "format", "message": f"unsupported format {format}"}],
        )
    data = await list_test_cases(project_id)
    items = data["items"]
    if cleaned_format == "csv":
        return {"format": "csv", "content": _render_csv(items)}
    if cleaned_format == "markdown":
        return {"format": "markdown", "content": _render_markdown(items)}
    return {"format": "json", "items": items}
