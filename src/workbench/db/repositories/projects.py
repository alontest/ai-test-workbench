"""项目上下文查询。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.db.models import ProjectContext


async def get(db: AsyncSession, project_id: int) -> ProjectContext | None:
    return await db.get(ProjectContext, project_id)


async def get_by_name_key(db: AsyncSession, name_key: str) -> ProjectContext | None:
    return await db.scalar(
        select(ProjectContext).where(ProjectContext.name_key == name_key)
    )


async def list_page(
    db: AsyncSession,
    *,
    limit: int,
    after: tuple[datetime, int] | None = None,
) -> list[ProjectContext]:
    statement = select(ProjectContext)
    if after is not None:
        moment, project_id = after
        statement = statement.where(
            or_(
                ProjectContext.updated_at < moment,
                and_(
                    ProjectContext.updated_at == moment,
                    ProjectContext.project_id < project_id,
                ),
            )
        )
    statement = statement.order_by(
        ProjectContext.updated_at.desc(), ProjectContext.project_id.desc()
    ).limit(limit)
    return list(await db.scalars(statement))
