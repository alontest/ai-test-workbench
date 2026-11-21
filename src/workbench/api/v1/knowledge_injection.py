"""会话知识注入：候选与只读预览（不落库、不调用模型）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from workbench.api.deps import require_same_origin
from workbench.api.pagination import decode_cursor
from workbench.api.schemas.knowledge import KnowledgePreviewRequest
from workbench.core.ports import KnowledgeRef
from workbench.services.knowledge.injection_service import KnowledgeInjectionService

router = APIRouter(
    prefix="/sessions", tags=["knowledge"], dependencies=[Depends(require_same_origin)]
)


def _service(request: Request) -> KnowledgeInjectionService:
    return KnowledgeInjectionService(
        sessionmaker=request.app.state.database.sessionmaker,
        settings=request.app.state.settings,
    )


@router.get("/{session_id}/knowledge-injection/candidates")
async def injection_candidates(
    session_id: int,
    request: Request,
    entry_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    limit: int = Query(50),
    cursor: str | None = None,
) -> dict[str, object]:
    return await _service(request).candidates(
        session_id=session_id,
        q=q,
        entry_type=entry_type,
        limit=limit,
        cursor=decode_cursor(cursor) if cursor else None,
    )


@router.post("/{session_id}/knowledge-injection/preview")
async def injection_preview(
    session_id: int, payload: KnowledgePreviewRequest, request: Request
) -> dict[str, object]:
    service = _service(request)
    detail = await service.session_project(session_id)
    refs = [
        KnowledgeRef(kb_id=item.kb_id, entry_codes=(item.code,))
        for item in payload.refs
    ]
    return await service.preview(
        project_id=detail,
        refs=refs,
        user_prompt=payload.user_prompt,
    )
