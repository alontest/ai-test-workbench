"""会话查询。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.db.models import AnalysisSession


async def get(db: AsyncSession, session_id: int) -> AnalysisSession | None:
    return await db.get(AnalysisSession, session_id)


async def list_recent(db: AsyncSession, *, limit: int = 10) -> list[AnalysisSession]:
    rows = await db.scalars(
        select(AnalysisSession)
        .order_by(AnalysisSession.updated_at.desc(), AnalysisSession.session_id.desc())
        .limit(limit)
    )
    return list(rows)
