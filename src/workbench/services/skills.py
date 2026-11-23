"""QA 技能库服务：内置 v0 种子、人工 CRUD、历史版本回滚与对话式 AI 修订提案。"""

from __future__ import annotations

import difflib
import re
from collections.abc import Sequence
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.api.serialization import to_rfc3339
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.errors import is_unique_violation
from workbench.db.models import ApprovalRequest, ProjectContext, QaSkill, QaSkillVersion
from workbench.services import calls as calls_service
from workbench.services import sessions as sessions_service
from workbench.services.ai_gateway import AiGateway
from workbench.services.errors import DomainError

VALID_SCOPES = frozenset({"global", "project"})
VALID_DOMAINS = frozenset(
    {"test-case", "diagnosis", "regression-list", "test-report", "general"}
)
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,99}$")
_CODE_FENCE_RE = re.compile(
    r"^\s*```(?:markdown|md)?\s*\n(.*?)\n```\s*$", re.DOTALL | re.IGNORECASE
)

BUILTIN_TEST_CASE_SKILL_SLUG = "two-stage-test-case-design"
BUILTIN_TEST_CASE_SKILL_NAME = "两阶段测试设计与用例生成规范"
BUILTIN_TEST_CASE_SKILL_DESC = (
    "先产出可勾选的测试设计检查点矩阵（阶段 1），确认后再生成带知识锚点与代码路径的结构化用例（阶段 2）。"
)
BUILTIN_TEST_CASE_SKILL_CONTENT = """# 两阶段测试设计与用例生成规范（v0 底座）

## 一、核心原则
1. **先设计后铺开**：禁止越过检查点确认直接倾倒海量低质量用例。
2. **双向证据锚定**：每条测试检查点与最终用例必须尽量关联注入的知识库条目编号（`kbCodes`）与真实代码路径（`codePaths`），严禁编造未出现的编号或路径。
3. **五维覆盖**：每个业务模块至少审视功能主路径（`functional`）、边界值（`boundary`）、异常与逆向流（`exception`）、权限与安全（`security`）、并发与幂等（`concurrency`）。

## 二、阶段 1：测试设计检查点矩阵（Checkpoint Matrix）
根据需求正文、注入的知识库条目及代码路径，输出 JSON 格式的检查点数组：
- `checkpointId`：稳定短标识（如 `CP-01`、`CP-02`）
- `module`：所属业务模块或特性层级（如 `订单中心/超时关单`）
- `scenario`：具体测试场景与检查点一句话描述
- `category`：`functional` | `boundary` | `exception` | `security` | `concurrency`
- `priority`：`P0` | `P1` | `P2` | `P3`
- `rationale`：为什么需要测这一项（引用知识规则或代码分支）
- `kbCodes`：关联的知识条目 code 数组（如 `["BR-001"]`）
- `codePaths`：关联的代码路径数组

## 三、阶段 2：结构化测试用例生成（Structured Test Cases）
仅针对测试人员勾选确认的检查点，逐条展开为可直接执行的测试用例 JSON 数组：
- `checkpointId`：对应阶段 1 的检查点 ID
- `caseCode`：可读用例编号（如 `TC-ORD-001`）
- `module`：模块层级路径（用于表格分组与层级树/类脑图展示）
- `title`：清晰描述「在什么条件下验证什么行为」
- `priority`：`P0` | `P1` | `P2` | `P3`
- `caseType`：`functional` | `boundary` | `exception` | `security` | `concurrency`
- `preconditions`：明确的前置状态与测试数据准备（字符串数组）
- `steps`：有序步骤数组 `[{"stepNo": 1, "action": "...", "expected": "..."}]`
- `expectedSummary`：总体预期结果与状态落库/事件断言
- `kbCodes`：继承并核实的知识条目编号数组
- `codePaths`：继承并核实的代码路径数组
"""


def serialize_skill(
    row: QaSkill,
    *,
    versions: Sequence[QaSkillVersion] | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "skillId": row.skill_id,
        "scope": row.scope,
        "projectId": row.project_id,
        "slug": row.slug,
        "name": row.name,
        "domain": row.domain,
        "description": row.description,
        "triggers": list(row.triggers or []),
        "contentMd": row.content_md,
        "currentVersion": row.current_version,
        "isBuiltin": bool(row.is_builtin),
        "createdAt": to_rfc3339(row.created_at),
        "updatedAt": to_rfc3339(row.updated_at),
    }
    if versions is not None:
        data["versions"] = [serialize_skill_version(v) for v in versions]
    return data


def serialize_skill_version(row: QaSkillVersion) -> dict[str, Any]:
    return {
        "versionId": row.version_id,
        "skillId": row.skill_id,
        "version": row.version,
        "contentMd": row.content_md,
        "changeSummary": row.change_summary,
        "sourceType": row.source_type,
        "approvalId": row.approval_id,
        "sessionId": row.session_id,
        "createdAt": to_rfc3339(row.created_at),
    }


def _scope_key_for(scope: str, project_id: int | None) -> str:
    if scope not in VALID_SCOPES:
        raise DomainError(
            "validation_error",
            "技能作用域必须为 global 或 project。",
            details=[{"field": "scope", "message": "invalid scope"}],
        )
    if scope == "global":
        if project_id is not None:
            raise DomainError(
                "validation_error",
                "全局技能不能绑定 projectId。",
                details=[{"field": "projectId", "message": "must be null for global"}],
            )
        return "global"
    if project_id is None:
        raise DomainError(
            "validation_error",
            "项目级技能必须指定 projectId。",
            details=[{"field": "projectId", "message": "required for project scope"}],
        )
    return f"project:{project_id}"


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


def _clean_slug(slug: str) -> str:
    cleaned = (slug or "").strip().lower()
    if not _SLUG_RE.match(cleaned):
        raise DomainError(
            "validation_error",
            "技能标识（slug）必须为 1–100 位小写字母、数字、连字符或下划线。",
            details=[{"field": "slug", "message": "invalid slug"}],
        )
    return cleaned


def _clean_domain(domain: str) -> str:
    cleaned = (domain or "").strip()
    if cleaned not in VALID_DOMAINS:
        raise DomainError(
            "validation_error",
            "无效的技能领域（domain）。",
            details=[{"field": "domain", "message": f"unsupported domain {cleaned}"}],
        )
    return cleaned


def _clean_triggers(triggers: Sequence[str] | None) -> list[str]:
    if not triggers:
        return []
    result: list[str] = []
    for item in triggers:
        cleaned = str(item).strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


async def ensure_builtin_skills(db: AsyncSession) -> QaSkill:
    """幂等初始化内置《两阶段测试设计与用例生成规范》v0。"""
    existing = await db.scalar(
        select(QaSkill).where(
            QaSkill.scope_key == "global",
            QaSkill.slug == BUILTIN_TEST_CASE_SKILL_SLUG,
        )
    )
    if existing is not None:
        return existing

    now = utcnow()
    skill_id = uuid4().hex
    skill = QaSkill(
        skill_id=skill_id,
        scope="global",
        scope_key="global",
        project_id=None,
        slug=BUILTIN_TEST_CASE_SKILL_SLUG,
        name=BUILTIN_TEST_CASE_SKILL_NAME,
        domain="test-case",
        description=BUILTIN_TEST_CASE_SKILL_DESC,
        triggers=["case-library"],
        content_md=BUILTIN_TEST_CASE_SKILL_CONTENT.strip(),
        current_version=1,
        is_builtin=True,
        created_at=now,
        updated_at=now,
    )
    version = QaSkillVersion(
        version_id=uuid4().hex,
        skill_id=skill_id,
        version=1,
        content_md=skill.content_md,
        change_summary="系统内置初始版本（v0 底座）",
        source_type="builtin",
        created_at=now,
    )
    db.add(skill)
    db.add(version)
    try:
        await db.commit()
    except DBAPIError as exc:
        await db.rollback()
        if is_unique_violation(exc):
            found = await db.scalar(
                select(QaSkill).where(
                    QaSkill.scope_key == "global",
                    QaSkill.slug == BUILTIN_TEST_CASE_SKILL_SLUG,
                )
            )
            if found is not None:
                return found
        raise
    await db.refresh(skill)
    return skill


async def list_skills(
    *,
    project_id: int | None = None,
    domain: str | None = None,
) -> list[dict[str, Any]]:
    if domain is not None:
        domain = _clean_domain(domain)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await ensure_builtin_skills(db)
        stmt = select(QaSkill)
        if project_id is not None:
            stmt = stmt.where(
                or_(QaSkill.scope == "global", QaSkill.project_id == project_id)
            )
        else:
            stmt = stmt.where(QaSkill.scope == "global")
        if domain is not None:
            stmt = stmt.where(QaSkill.domain == domain)
        stmt = stmt.order_by(
            QaSkill.is_builtin.desc(),
            QaSkill.scope.asc(),
            QaSkill.updated_at.desc(),
            QaSkill.slug.asc(),
        )
        rows = (await db.scalars(stmt)).all()
        return [serialize_skill(row) for row in rows]


async def _load_versions(db: AsyncSession, skill_id: str) -> list[QaSkillVersion]:
    stmt = (
        select(QaSkillVersion)
        .where(QaSkillVersion.skill_id == skill_id)
        .order_by(QaSkillVersion.version.desc())
    )
    return list((await db.scalars(stmt)).all())


async def get_skill(skill_id: str) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await ensure_builtin_skills(db)
        row = await db.get(QaSkill, skill_id)
        if row is None:
            raise DomainError(
                "skill_not_found",
                "QA 技能不存在。",
                status_code=404,
                details=[{"field": "skillId", "message": "skill not found"}],
            )
        versions = await _load_versions(db, skill_id)
        return serialize_skill(row, versions=versions)


async def create_skill(
    *,
    scope: str,
    project_id: int | None = None,
    slug: str,
    name: str,
    domain: str = "test-case",
    description: str,
    triggers: Sequence[str] | None = None,
    content_md: str,
    change_summary: str = "人工创建初始版本",
) -> dict[str, Any]:
    scope_key = _scope_key_for(scope, project_id)
    cleaned_slug = _clean_slug(slug)
    cleaned_name = _clean_required(name, field="name", max_len=200)
    cleaned_domain = _clean_domain(domain)
    cleaned_desc = _clean_required(description, field="description", max_len=500)
    cleaned_content = _clean_required(content_md, field="contentMd")
    cleaned_summary = _clean_required(
        change_summary or "人工创建初始版本", field="changeSummary", max_len=500
    )
    cleaned_triggers = _clean_triggers(triggers)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await ensure_builtin_skills(db)
        if project_id is not None:
            project = await db.get(ProjectContext, project_id)
            if project is None:
                raise DomainError(
                    "project_not_found",
                    "项目不存在。",
                    status_code=404,
                    details=[{"field": "projectId", "message": "project not found"}],
                )
        dup = await db.scalar(
            select(QaSkill).where(
                QaSkill.scope_key == scope_key,
                QaSkill.slug == cleaned_slug,
            )
        )
        if dup is not None:
            raise DomainError(
                "skill_slug_duplicate",
                "同作用域下已存在相同标识的技能。",
                status_code=409,
                details=[{"field": "slug", "message": "技能标识已存在"}],
            )
        now = utcnow()
        skill_id = uuid4().hex
        row = QaSkill(
            skill_id=skill_id,
            scope=scope,
            scope_key=scope_key,
            project_id=project_id,
            slug=cleaned_slug,
            name=cleaned_name,
            domain=cleaned_domain,
            description=cleaned_desc,
            triggers=cleaned_triggers,
            content_md=cleaned_content,
            current_version=1,
            is_builtin=False,
            created_at=now,
            updated_at=now,
        )
        ver = QaSkillVersion(
            version_id=uuid4().hex,
            skill_id=skill_id,
            version=1,
            content_md=cleaned_content,
            change_summary=cleaned_summary,
            source_type="human",
            created_at=now,
        )
        db.add(row)
        db.add(ver)
        try:
            await db.commit()
        except DBAPIError as exc:
            await db.rollback()
            if is_unique_violation(exc):
                raise DomainError(
                    "skill_slug_duplicate",
                    "同作用域下已存在相同标识的技能。",
                    status_code=409,
                    details=[{"field": "slug", "message": "技能标识已存在"}],
                ) from exc
            raise
        await db.refresh(row)
        versions = await _load_versions(db, skill_id)
        return serialize_skill(row, versions=versions)


async def update_skill(
    skill_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    domain: str | None = None,
    triggers: Sequence[str] | None = None,
    content_md: str,
    change_summary: str = "人工修订技能正文",
) -> dict[str, Any]:
    cleaned_content = _clean_required(content_md, field="contentMd")
    cleaned_summary = _clean_required(
        change_summary or "人工修订技能正文", field="changeSummary", max_len=500
    )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(QaSkill, skill_id)
        if row is None:
            raise DomainError(
                "skill_not_found",
                "QA 技能不存在。",
                status_code=404,
                details=[{"field": "skillId", "message": "skill not found"}],
            )
        if name is not None:
            row.name = _clean_required(name, field="name", max_len=200)
        if description is not None:
            row.description = _clean_required(
                description, field="description", max_len=500
            )
        if domain is not None:
            row.domain = _clean_domain(domain)
        if triggers is not None:
            row.triggers = _clean_triggers(triggers)

        now = utcnow()
        row.current_version = int(row.current_version) + 1
        row.content_md = cleaned_content
        row.updated_at = now

        ver = QaSkillVersion(
            version_id=uuid4().hex,
            skill_id=row.skill_id,
            version=row.current_version,
            content_md=cleaned_content,
            change_summary=cleaned_summary,
            source_type="human",
            created_at=now,
        )
        db.add(ver)
        await db.commit()
        await db.refresh(row)
        versions = await _load_versions(db, row.skill_id)
        return serialize_skill(row, versions=versions)


async def rollback_skill(
    skill_id: str,
    *,
    target_version: int,
    change_summary: str | None = None,
) -> dict[str, Any]:
    if target_version < 1:
        raise DomainError(
            "validation_error",
            "目标版本号必须大于等于 1。",
            details=[{"field": "targetVersion", "message": "must be >= 1"}],
        )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(QaSkill, skill_id)
        if row is None:
            raise DomainError(
                "skill_not_found",
                "QA 技能不存在。",
                status_code=404,
                details=[{"field": "skillId", "message": "skill not found"}],
            )
        target_row = await db.scalar(
            select(QaSkillVersion).where(
                QaSkillVersion.skill_id == skill_id,
                QaSkillVersion.version == target_version,
            )
        )
        if target_row is None:
            raise DomainError(
                "skill_version_not_found",
                "目标历史版本不存在。",
                status_code=404,
                details=[
                    {
                        "field": "targetVersion",
                        "message": f"version {target_version} not found",
                    }
                ],
            )
        now = utcnow()
        row.current_version = int(row.current_version) + 1
        row.content_md = target_row.content_md
        row.updated_at = now
        summary = _clean_required(
            change_summary or f"回滚至历史版本 v{target_version}",
            field="changeSummary",
            max_len=500,
        )
        ver = QaSkillVersion(
            version_id=uuid4().hex,
            skill_id=row.skill_id,
            version=row.current_version,
            content_md=target_row.content_md,
            change_summary=summary,
            source_type="rollback",
            created_at=now,
        )
        db.add(ver)
        await db.commit()
        await db.refresh(row)
        versions = await _load_versions(db, row.skill_id)
        return serialize_skill(row, versions=versions)


def compute_unified_diff(
    before_content: str,
    after_content: str,
    *,
    slug: str,
    base_version: int,
) -> str:
    before_lines = before_content.splitlines()
    after_lines = after_content.splitlines()
    diff_lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{slug}.md (v{base_version})",
            tofile=f"b/{slug}.md (proposed)",
            lineterm="",
        )
    )
    return "\n".join(diff_lines)


def _extract_proposed_markdown(
    raw_output: str, *, before_content: str, instruction: str
) -> str:
    cleaned = (raw_output or "").strip()
    fence_match = _CODE_FENCE_RE.match(cleaned)
    if fence_match:
        cleaned = fence_match.group(1).strip()
    if not cleaned or cleaned == before_content.strip():
        cleaned = (
            f"{before_content.rstrip()}\n\n"
            f"## 补充规范（AI 提案）\n- {instruction.strip()}\n"
        ).strip()
    return cleaned


async def propose_skill_revision(
    skill_id: str,
    *,
    project_id: int | None = None,
    model_id: int | None = None,
    session_id: int | None = None,
    instruction: str,
    gateway: AiGateway | None = None,
) -> dict[str, Any]:
    """对话式修订提案：经唯一模型出口生成新全文与 Unified Diff，创建 pending 审批单。"""
    from workbench.services.approvals import serialize_approval

    cleaned_instruction = _clean_required(
        instruction, field="instruction", max_len=1000
    )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await ensure_builtin_skills(db)
        skill = await db.get(QaSkill, skill_id)
        if skill is None:
            raise DomainError(
                "skill_not_found",
                "QA 技能不存在。",
                status_code=404,
                details=[{"field": "skillId", "message": "skill not found"}],
            )
        skill_name = skill.name
        skill_slug = skill.slug
        base_version = int(skill.current_version)
        before_content = skill.content_md
        default_project_id = project_id if project_id is not None else skill.project_id

    if session_id is not None:
        session_detail = await sessions_service.get_session(session_id)
        resolved_session_id = session_id
        resolved_project_id = session_detail["project"]["projectId"]
    else:
        if default_project_id is None:
            raise DomainError(
                "validation_error",
                "生成 AI 修订提案需要指定 projectId 或 sessionId。",
                details=[{"field": "projectId", "message": "required"}],
            )
        if model_id is None:
            raise DomainError(
                "validation_error",
                "生成 AI 修订提案需要指定 modelId 或 sessionId。",
                details=[{"field": "modelId", "message": "required"}],
            )
        created_session = await sessions_service.create(
            project_id=default_project_id,
            entrance_key="case-library",
            title=f"技能修订：{skill_name}"[:200],
            model_id=model_id,
        )
        resolved_session_id = created_session["session_id"]
        resolved_project_id = default_project_id

    await sessions_service.append_event(
        resolved_session_id,
        "input_text",
        {
            "title": f"技能修订指令：{skill_name}",
            "text": cleaned_instruction,
            "charCount": len(cleaned_instruction),
        },
    )

    prompt = (
        f"你正在协助修订 QA 技能《{skill_name}》（标识：`{skill_slug}`，当前版本：v{base_version}）。\n"
        f"请严格根据以下修订指令，在保留原有核心结构的基础上输出修订后的**完整 Markdown 全文**（不要只输出片段）：\n\n"
        f"【修订指令】\n{cleaned_instruction}\n\n"
        f"【当前技能 Markdown（v{base_version}）】\n{before_content}\n"
    )
    call_result = await calls_service.complete(
        resolved_session_id,
        prompt=prompt,
        gateway=gateway,
    )
    after_content = _extract_proposed_markdown(
        str(call_result.get("resultText") or ""),
        before_content=before_content,
        instruction=cleaned_instruction,
    )
    unified_diff = compute_unified_diff(
        before_content,
        after_content,
        slug=skill_slug,
        base_version=base_version,
    )

    async with sessionmaker() as db:
        approval = ApprovalRequest(
            approval_id=uuid4().hex,
            project_id=resolved_project_id,
            session_id=resolved_session_id,
            call_id=call_result["callId"],
            target_type="qa_skill",
            target_id=skill_id,
            target_title=skill_name,
            action_type="update_skill",
            base_version=base_version,
            before_content=before_content,
            after_content=after_content,
            unified_diff=unified_diff,
            rationale=cleaned_instruction,
            status="pending",
            created_at=utcnow(),
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return serialize_approval(approval)
