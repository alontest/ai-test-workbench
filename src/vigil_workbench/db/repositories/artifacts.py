"""制品查询。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.db.models import Artifact


async def get(db: AsyncSession, artifact_id: int) -> Artifact | None:
    return await db.get(Artifact, artifact_id)


async def existing_file_name_keys(db: AsyncSession, session_id: int) -> set[str]:
    rows = await db.scalars(
        select(Artifact.file_name_key).where(Artifact.session_id == session_id)
    )
    return {row.casefold() for row in rows.all()}


async def list_for_session(db: AsyncSession, session_id: int) -> list[Artifact]:
    rows = await db.scalars(
        select(Artifact)
        .where(Artifact.session_id == session_id)
        .order_by(Artifact.artifact_id.asc())
    )
    return list(rows)
