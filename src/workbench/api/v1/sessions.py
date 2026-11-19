"""会话、时间线与文本输入接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response

from workbench.api.deps import require_same_origin
from workbench.api.pagination import decode_cursor
from workbench.api.schemas.session import SessionCreate, TextInputCreate
from workbench.services import sessions

router = APIRouter(
    prefix="/sessions", tags=["sessions"], dependencies=[Depends(require_same_origin)]
)


@router.get("")
async def list_sessions(
    request: Request,
    project_id: int | None = Query(None, alias="projectId"),
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await sessions.list_sessions(
        project_id=project_id, status=status, limit=limit, cursor=decoded
    )
    return {"items": items, "nextCursor": next_cursor}


@router.post("", status_code=201)
async def create_session(payload: SessionCreate) -> dict[str, object]:
    view = await sessions.create(
        project_id=payload.project_id,
        entrance_key=payload.entrance_key,  # type: ignore[arg-type]
        title=payload.title,
        model_id=payload.model_id,
    )
    return await sessions.get_session(view["session_id"])


@router.get("/{session_id}")
async def get_session(session_id: int, request: Request) -> dict[str, object]:
    request.state.session_id = session_id
    return await sessions.get_session(session_id)


@router.post("/{session_id}/complete")
async def complete_session(session_id: int, request: Request) -> dict[str, object]:
    request.state.session_id = session_id
    await sessions.complete_session(session_id)
    return await sessions.get_session(session_id)


@router.delete("/{session_id}", status_code=204)
async def delete_session(session_id: int) -> Response:
    await sessions.delete_session(session_id)
    return Response(status_code=204)


@router.get("/{session_id}/events")
async def list_events(
    session_id: int,
    request: Request,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = None,
) -> dict[str, object]:
    request.state.session_id = session_id
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await sessions.list_events_page(
        session_id, limit=limit, cursor=decoded
    )
    return {
        "items": [sessions.event_to_api(item) for item in items],
        "nextCursor": next_cursor,
    }


@router.post("/{session_id}/inputs/text", status_code=201)
async def append_text_input(
    session_id: int, payload: TextInputCreate, request: Request
) -> dict[str, object]:
    request.state.session_id = session_id
    view = await sessions.append_text_input(
        session_id, title=payload.title, text=payload.text
    )
    return sessions.event_to_api(view)
