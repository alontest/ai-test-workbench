"""会话内调用接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from workbench.api.deps import require_same_origin
from workbench.api.pagination import decode_cursor
from workbench.api.schemas.call import CallCompleteRequest
from workbench.services import calls as calls_service

router = APIRouter(tags=["calls"], dependencies=[Depends(require_same_origin)])


def _gateway(request: Request):  # noqa: ANN202
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is None:
        from workbench.services.ai_gateway import AiGateway

        gateway = AiGateway()
        request.app.state.ai_gateway = gateway
    return gateway


@router.post("/sessions/{session_id}/ai/complete")
async def complete_call(
    session_id: int, payload: CallCompleteRequest, request: Request
) -> dict[str, object]:
    request.state.session_id = session_id
    return await calls_service.complete(
        session_id,
        prompt=payload.prompt,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        knowledge_refs=payload.knowledge_refs,
        confirm_invalid_codes=payload.confirm_invalid_codes,
        gateway=_gateway(request),
    )


@router.get("/calls")
async def list_calls(
    session_id: int | None = Query(None, alias="sessionId"),
    project_id: int | None = Query(None, alias="projectId"),
    status: str | None = None,
    created_from: str | None = Query(None, alias="from"),
    created_to: str | None = Query(None, alias="to"),
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await calls_service.list_calls(
        session_id=session_id,
        project_id=project_id,
        status=status,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=decoded,
    )
    return {"items": items, "nextCursor": next_cursor}


@router.get("/calls/{call_id}")
async def get_call(call_id: int) -> dict[str, object]:
    return await calls_service.get_call(call_id)
