"""调用记录查询。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.db.models import AiCallRecord, AnalysisSession, ProjectContext


async def get_with_project(
    db: AsyncSession, call_id: int
) -> tuple[AiCallRecord, ProjectContext] | None:
    statement = (
        select(AiCallRecord, ProjectContext)
        .join(AnalysisSession, AiCallRecord.session_id == AnalysisSession.session_id)
        .join(ProjectContext, AnalysisSession.project_id == ProjectContext.project_id)
        .where(AiCallRecord.call_id == call_id)
    )
    row = (await db.execute(statement)).first()
    if row is None:
        return None
    return row[0], row[1]


async def list_with_project(
    db: AsyncSession,
    *,
    session_id: int | None,
    project_id: int | None,
    status: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    after: tuple[datetime, int] | None,
    limit: int,
) -> list[tuple[AiCallRecord, ProjectContext]]:
    statement = (
        select(AiCallRecord, ProjectContext)
        .join(AnalysisSession, AiCallRecord.session_id == AnalysisSession.session_id)
        .join(ProjectContext, AnalysisSession.project_id == ProjectContext.project_id)
    )
    if session_id is not None:
        statement = statement.where(AiCallRecord.session_id == session_id)
    if project_id is not None:
        statement = statement.where(AnalysisSession.project_id == project_id)
    if status is not None:
        statement = statement.where(AiCallRecord.status == status)
    if created_from is not None:
        statement = statement.where(AiCallRecord.created_at >= created_from)
    if created_to is not None:
        statement = statement.where(AiCallRecord.created_at <= created_to)
    if after is not None:
        moment, call_id = after
        statement = statement.where(
            (AiCallRecord.created_at < moment)
            | (
                (AiCallRecord.created_at == moment)
                & (AiCallRecord.call_id < call_id)
            )
        )
    statement = statement.order_by(
        AiCallRecord.created_at.desc(), AiCallRecord.call_id.desc()
    ).limit(limit)
    return list(await db.execute(statement))
