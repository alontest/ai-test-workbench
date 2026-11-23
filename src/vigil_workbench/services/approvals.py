"""审批中心轻量版服务（Human-in-the-Loop 闸门）：列表、详情、批准落盘与驳回保留。"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select

from vigil_workbench.api.serialization import to_rfc3339
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.models import ApprovalRequest, QaSkill, QaSkillVersion
from vigil_workbench.services.errors import DomainError

VALID_APPROVAL_STATUSES = frozenset({"pending", "approved", "rejected"})


def serialize_approval(row: ApprovalRequest) -> dict[str, Any]:
    return {
        "approvalId": row.approval_id,
        "projectId": row.project_id,
        "sessionId": row.session_id,
        "callId": row.call_id,
        "targetType": row.target_type,
        "targetId": row.target_id,
        "targetTitle": row.target_title,
        "actionType": row.action_type,
        "baseVersion": row.base_version,
        "beforeContent": row.before_content,
        "afterContent": row.after_content,
        "unifiedDiff": row.unified_diff,
        "rationale": row.rationale,
        "status": row.status,
        "decisionNote": row.decision_note,
        "appliedVersion": row.applied_version,
        "createdAt": to_rfc3339(row.created_at),
        "decidedAt": to_rfc3339(row.decided_at),
    }


def _clean_note(note: str | None) -> str | None:
    if note is None:
        return None
    cleaned = note.strip()
    if len(cleaned) > 500:
        raise DomainError(
            "validation_error",
            "审批备注长度不能超过 500 个字符。",
            details=[{"field": "decisionNote", "message": "长度上限 500"}],
        )
    return cleaned or None


async def list_approvals(
    *,
    status: str | None = None,
    project_id: int | None = None,
) -> list[dict[str, Any]]:
    if status is not None and status not in VALID_APPROVAL_STATUSES:
        raise DomainError(
            "validation_error",
            "无效的审批状态过滤值。",
            details=[{"field": "status", "message": f"invalid status {status}"}],
        )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        stmt = select(ApprovalRequest)
        if status is not None:
            stmt = stmt.where(ApprovalRequest.status == status)
        if project_id is not None:
            stmt = stmt.where(ApprovalRequest.project_id == project_id)
        stmt = stmt.order_by(
            ApprovalRequest.created_at.desc(),
            ApprovalRequest.approval_id.desc(),
        )
        rows = (await db.scalars(stmt)).all()
        return [serialize_approval(row) for row in rows]


async def get_approval(approval_id: str) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(ApprovalRequest, approval_id)
        if row is None:
            raise DomainError(
                "approval_not_found",
                "审批单不存在。",
                status_code=404,
                details=[{"field": "approvalId", "message": "approval not found"}],
            )
        return serialize_approval(row)


async def approve_request(
    approval_id: str,
    *,
    decision_note: str | None = None,
) -> dict[str, Any]:
    """批准提案：单事务更新目标 qa_skill、追加 qa_skill_version 并标记 approved。"""
    cleaned_note = _clean_note(decision_note)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(ApprovalRequest, approval_id)
        if row is None:
            raise DomainError(
                "approval_not_found",
                "审批单不存在。",
                status_code=404,
                details=[{"field": "approvalId", "message": "approval not found"}],
            )
        if row.status != "pending":
            raise DomainError(
                "approval_already_decided",
                "该审批单已处理，不能重复审批。",
                status_code=409,
                details=[
                    {
                        "field": "status",
                        "message": f"approval already {row.status}",
                    }
                ],
            )
        skill = await db.get(QaSkill, row.target_id)
        if skill is None:
            raise DomainError(
                "skill_not_found",
                "目标 QA 技能不存在。",
                status_code=404,
                details=[{"field": "targetId", "message": "target skill not found"}],
            )

        now = utcnow()
        new_version = int(skill.current_version) + 1
        skill.current_version = new_version
        skill.content_md = row.after_content
        skill.updated_at = now

        summary = (
            cleaned_note or f"批准 AI 修订提案：{row.rationale}"
        )[:500]
        ver = QaSkillVersion(
            version_id=uuid4().hex,
            skill_id=skill.skill_id,
            version=new_version,
            content_md=row.after_content,
            change_summary=summary,
            source_type="agent_proposal",
            approval_id=row.approval_id,
            session_id=row.session_id,
            created_at=now,
        )
        db.add(ver)

        row.status = "approved"
        row.decision_note = cleaned_note
        row.applied_version = new_version
        row.decided_at = now

        await db.commit()
        await db.refresh(row)
        return serialize_approval(row)


async def reject_request(
    approval_id: str,
    *,
    decision_note: str | None = None,
) -> dict[str, Any]:
    """驳回提案：标记 rejected 并保留意见，目标 qa_skill 完全不变。"""
    cleaned_note = _clean_note(decision_note)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(ApprovalRequest, approval_id)
        if row is None:
            raise DomainError(
                "approval_not_found",
                "审批单不存在。",
                status_code=404,
                details=[{"field": "approvalId", "message": "approval not found"}],
            )
        if row.status != "pending":
            raise DomainError(
                "approval_already_decided",
                "该审批单已处理，不能重复审批。",
                status_code=409,
                details=[
                    {
                        "field": "status",
                        "message": f"approval already {row.status}",
                    }
                ],
            )
        row.status = "rejected"
        row.decision_note = cleaned_note
        row.decided_at = utcnow()
        await db.commit()
        await db.refresh(row)
        return serialize_approval(row)
