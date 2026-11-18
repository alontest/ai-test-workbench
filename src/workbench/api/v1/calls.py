"""会话内调用接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from workbench.api.deps import require_same_origin
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
        gateway=_gateway(request),
    )
