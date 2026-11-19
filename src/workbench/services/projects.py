"""项目上下文：创建、编辑与游标分页（无删除入口）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.exc import DBAPIError

from workbench.api.pagination import encode_cursor
from workbench.core.validation import optional_text, require_http_url, require_text
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.errors import is_unique_violation
from workbench.db.models import ProjectContext
from workbench.db.repositories import projects as projects_repo
from workbench.services.errors import DomainError

UNSET: Any = object()

_NAME_MAX = 100
_SHORT_TEXT_MAX = 500


def to_view(row: ProjectContext) -> dict[str, Any]:
    return {
        "projectId": row.project_id,
        "name": row.name,
        "repoUrl": row.repo_url,
        "techStack": row.tech_stack,
        "requirementSource": row.requirement_source,
        "notes": row.notes,
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
    }


def _duplicate() -> DomainError:
    return DomainError(
        "project_name_duplicate",
        "项目名称已存在。",
        status_code=409,
        details=[{"field": "name", "message": "项目名称已存在"}],
    )


async def create(
    *,
    name: str,
    repo_url: str | None = None,
    tech_stack: str | None = None,
    requirement_source: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    cleaned_name = require_text(name, field="name", max_length=_NAME_MAX)
    cleaned_url = (
        require_http_url(repo_url, field="repoUrl") if repo_url is not None else None
    )
    cleaned_stack = optional_text(tech_stack, field="techStack", max_length=_SHORT_TEXT_MAX)
    now = utcnow()
    row = ProjectContext(
        name=cleaned_name,
        name_key=cleaned_name.casefold(),
        repo_url=cleaned_url,
        tech_stack=cleaned_stack,
        requirement_source=requirement_source,
        notes=notes,
        created_at=now,
        updated_at=now,
    )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        if await projects_repo.get_by_name_key(db, row.name_key) is not None:
            raise _duplicate()
        db.add(row)
        try:
            await db.commit()
        except DBAPIError as exc:
            await db.rollback()
            if is_unique_violation(exc):
                raise _duplicate() from exc
            raise
        await db.refresh(row)
        return to_view(row)


async def get(project_id: int) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await projects_repo.get(db, project_id)
        if row is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "项目不存在"}],
            )
        return to_view(row)


async def update(
    project_id: int,
    *,
    name: str | None | Any = UNSET,
    repo_url: str | None | Any = UNSET,
    tech_stack: str | None | Any = UNSET,
    requirement_source: str | None | Any = UNSET,
    notes: str | None | Any = UNSET,
) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await projects_repo.get(db, project_id)
        if row is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "项目不存在"}],
            )
        if name is not UNSET:
            cleaned = require_text(name, field="name", max_length=_NAME_MAX)
            key = cleaned.casefold()
            if key != row.name_key:
                existing = await projects_repo.get_by_name_key(db, key)
                if existing is not None:
                    raise _duplicate()
            row.name = cleaned
            row.name_key = key
        if repo_url is not UNSET:
            row.repo_url = (
                require_http_url(repo_url, field="repoUrl")
                if repo_url is not None
                else None
            )
        if tech_stack is not UNSET:
            row.tech_stack = optional_text(
                tech_stack, field="techStack", max_length=_SHORT_TEXT_MAX
            )
        if requirement_source is not UNSET:
            row.requirement_source = requirement_source
        if notes is not UNSET:
            row.notes = notes
        row.updated_at = _bump(row.updated_at, utcnow())
        try:
            await db.commit()
        except DBAPIError as exc:
            await db.rollback()
            if is_unique_violation(exc):
                raise _duplicate() from exc
            raise
        await db.refresh(row)
        return to_view(row)


async def list_page(
    *, limit: int = 20, cursor: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], str | None]:
    after: tuple[datetime, int] | None = None
    if cursor is not None:
        from datetime import datetime as _dt

        raw_time = cursor.get("updated_at")
        raw_id = cursor.get("project_id")
        if not isinstance(raw_time, str) or not isinstance(raw_id, int):
            raise DomainError("validation_error", "游标非法。")
        after = (_dt.fromisoformat(raw_time.replace("Z", "+00:00")).replace(tzinfo=None), raw_id)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        rows = await projects_repo.list_page(db, limit=limit + 1, after=after)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            {"updated_at": last.updated_at.isoformat(), "project_id": last.project_id}
        )
    return [to_view(row) for row in page], next_cursor


def _bump(previous: datetime, now: datetime) -> datetime:
    if now <= previous:
        return previous.replace(microsecond=min(previous.microsecond + 1, 999999))
    return now
