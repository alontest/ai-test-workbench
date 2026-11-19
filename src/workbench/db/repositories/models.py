"""模型绑定查询。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.db.models import ModelBinding, ProviderConfig


async def get(db: AsyncSession, model_id: int) -> ModelBinding | None:
    return await db.get(ModelBinding, model_id)


async def get_by_name_key(
    db: AsyncSession, provider_id: int, model_name_key: str
) -> ModelBinding | None:
    return await db.scalar(
        select(ModelBinding).where(
            ModelBinding.provider_id == provider_id,
            ModelBinding.model_name_key == model_name_key,
        )
    )


async def list_page(
    db: AsyncSession,
    *,
    limit: int,
    provider_id: int | None = None,
    enabled_only: bool = False,
    after: tuple[datetime, int] | None = None,
) -> list[tuple[ModelBinding, ProviderConfig]]:
    statement = select(ModelBinding, ProviderConfig).join(
        ProviderConfig, ProviderConfig.provider_id == ModelBinding.provider_id
    )
    if provider_id is not None:
        statement = statement.where(ModelBinding.provider_id == provider_id)
    if enabled_only:
        statement = statement.where(
            ModelBinding.enabled.is_(True), ProviderConfig.enabled.is_(True)
        )
    if after is not None:
        moment, model_id = after
        statement = statement.where(
            or_(
                ModelBinding.created_at < moment,
                and_(
                    ModelBinding.created_at == moment, ModelBinding.model_id < model_id
                ),
            )
        )
    statement = statement.order_by(
        ModelBinding.created_at.desc(), ModelBinding.model_id.desc()
    ).limit(limit)
    rows = await db.execute(statement)
    return [(row[0], row[1]) for row in rows.all()]
