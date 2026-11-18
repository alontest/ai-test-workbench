"""时间线事件查询。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.db.models import SessionEvent


async def list_for_session(db: AsyncSession, session_id: int) -> list[SessionEvent]:
    rows = await db.scalars(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.event_id.asc())
    )
    return list(rows)


async def latest_for_session(db: AsyncSession, session_id: int) -> SessionEvent | None:
    return await db.scalar(
        select(SessionEvent)
        .where(SessionEvent.session_id == session_id)
        .order_by(SessionEvent.event_id.desc())
        .limit(1)
    )
