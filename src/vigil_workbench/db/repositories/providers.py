"""提供商查询。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.db.models import ProviderConfig


async def get(db: AsyncSession, provider_id: int) -> ProviderConfig | None:
    return await db.get(ProviderConfig, provider_id)


async def list_page(
    db: AsyncSession, *, limit: int, after: tuple[datetime, int] | None = None
) -> list[ProviderConfig]:
    statement = select(ProviderConfig)
    if after is not None:
        moment, provider_id = after
        statement = statement.where(
            or_(
                ProviderConfig.updated_at < moment,
                and_(
                    ProviderConfig.updated_at == moment,
                    ProviderConfig.provider_id < provider_id,
                ),
            )
        )
    statement = statement.order_by(
        ProviderConfig.updated_at.desc(), ProviderConfig.provider_id.desc()
    ).limit(limit)
    return list(await db.scalars(statement))
