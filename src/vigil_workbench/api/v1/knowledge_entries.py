"""知识库条目浏览与检索接口（全局）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.api.pagination import decode_cursor
from vigil_workbench.services.knowledge.query_service import KnowledgeQueryService

router = APIRouter(
    tags=["knowledge"], dependencies=[Depends(require_same_origin)]
)


@router.get("/knowledge-entries")
async def list_knowledge_entries(
    project_id: int | None = Query(None, alias="projectId"),
    kb_id: str | None = Query(None, alias="kbId"),
    entry_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    include_superseded: bool = Query(False, alias="includeSuperseded"),
    limit: int = Query(50),
    cursor: str | None = None,
) -> dict[str, object]:
    return await KnowledgeQueryService().search_entries(
        project_id=project_id,
        kb_id=kb_id,
        entry_type=entry_type,
        q=q,
        include_superseded=include_superseded,
        limit=limit,
        cursor=decode_cursor(cursor) if cursor else None,
    )


@router.get("/knowledge-entries/{entry_id}")
async def get_knowledge_entry(entry_id: str) -> dict[str, object]:
    return await KnowledgeQueryService().get_entry(entry_id)
