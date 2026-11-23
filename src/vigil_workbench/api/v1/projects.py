"""项目上下文接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.api.pagination import decode_cursor
from vigil_workbench.api.schemas.project import ProjectCreate, ProjectUpdate
from vigil_workbench.services import projects

router = APIRouter(
    prefix="/projects", tags=["projects"], dependencies=[Depends(require_same_origin)]
)


@router.get("")
async def list_projects(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await projects.list_page(limit=limit, cursor=decoded)
    return {"items": items, "nextCursor": next_cursor}


@router.post("", status_code=201)
async def create_project(payload: ProjectCreate) -> dict[str, object]:
    return await projects.create(
        name=payload.name,
        repo_url=payload.repo_url,
        tech_stack=payload.tech_stack,
        requirement_source=payload.requirement_source,
        notes=payload.notes,
    )


@router.get("/{project_id}")
async def get_project(project_id: int) -> dict[str, object]:
    return await projects.get(project_id)


@router.patch("/{project_id}")
async def update_project(
    project_id: int, payload: ProjectUpdate
) -> dict[str, object]:
    fields = payload.model_dump(exclude_unset=True)
    return await projects.update(project_id, **fields)
