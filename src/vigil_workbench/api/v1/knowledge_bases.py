"""知识库接口：导入（批次 B）与浏览（批次 C）。删除属批次 D。"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, Response, UploadFile

from vigil_workbench.adapters.fs.knowledge_storage import KbStorage
from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.api.pagination import decode_cursor
from vigil_workbench.api.schemas.knowledge import (
    KnowledgeImportForm,
    KnowledgeImportResponse,
)
from vigil_workbench.services.knowledge import KnowledgeImportService
from vigil_workbench.services.knowledge.lifecycle_service import KnowledgeLifecycleService
from vigil_workbench.services.knowledge.query_service import KnowledgeQueryService

router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge"],
    dependencies=[Depends(require_same_origin)],
)


@router.post("", status_code=201, response_model=KnowledgeImportResponse)
async def import_knowledge_base(
    form: Annotated[KnowledgeImportForm, Form()],
    files: Annotated[list[UploadFile], File(...)],
) -> dict[str, object]:
    service = KnowledgeImportService()
    return await service.import_files(
        project_id=form.project_id, name=form.name, files=files
    )


@router.get("")
async def list_knowledge_bases(
    project_id: int | None = Query(None, alias="projectId"),
    include_superseded: bool = Query(False, alias="includeSuperseded"),
    limit: int = Query(50),
    cursor: str | None = None,
) -> dict[str, object]:
    return await KnowledgeQueryService().list_bases(
        project_id=project_id,
        include_superseded=include_superseded,
        limit=limit,
        cursor=decode_cursor(cursor) if cursor else None,
    )


@router.get("/{kb_id}/versions")
async def list_knowledge_base_versions(kb_id: str) -> dict[str, object]:
    return await KnowledgeQueryService().list_versions(kb_id)


@router.get("/{kb_id}/entries")
async def list_knowledge_base_entries(
    kb_id: str,
    entry_type: str | None = Query(None, alias="type"),
    q: str | None = None,
    limit: int = Query(50),
    cursor: str | None = None,
) -> dict[str, object]:
    return await KnowledgeQueryService().search_entries(
        kb_id=kb_id,
        entry_type=entry_type,
        q=q,
        limit=limit,
        cursor=decode_cursor(cursor) if cursor else None,
    )


@router.get("/{kb_id}")
async def get_knowledge_base(kb_id: str) -> dict[str, object]:
    return await KnowledgeQueryService().get_base(kb_id)


@router.delete("/{kb_id}", status_code=204)
async def delete_knowledge_base(kb_id: str, request: Request) -> Response:
    settings = request.app.state.settings
    service = KnowledgeLifecycleService(
        sessionmaker=request.app.state.database.sessionmaker,
        storage=KbStorage(root=settings.data_path / "knowledge-bases"),
    )
    await service.delete_logical(kb_id)
    return Response(status_code=204)
