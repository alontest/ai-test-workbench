"""审批中心接口（/api/v1/approvals）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.services import approvals as approvals_service

router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
    dependencies=[Depends(require_same_origin)],
)


class ApprovalDecisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    decision_note: str | None = Field(default=None, alias="decisionNote")


@router.get("")
async def list_approvals(
    status: str | None = Query(default=None),
    project_id: int | None = Query(default=None, alias="projectId"),
) -> dict[str, object]:
    items = await approvals_service.list_approvals(
        status=status,
        project_id=project_id,
    )
    return {"items": items}


@router.get("/{approval_id}")
async def get_approval(approval_id: str) -> dict[str, object]:
    return await approvals_service.get_approval(approval_id)


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    payload: ApprovalDecisionRequest | None = None,
) -> dict[str, object]:
    note = payload.decision_note if payload is not None else None
    return await approvals_service.approve_request(
        approval_id, decision_note=note
    )


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    payload: ApprovalDecisionRequest | None = None,
) -> dict[str, object]:
    note = payload.decision_note if payload is not None else None
    return await approvals_service.reject_request(
        approval_id, decision_note=note
    )
