"""模型登记与查询接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from workbench.api.deps import require_same_origin
from workbench.api.pagination import decode_cursor
from workbench.api.schemas.model import ModelCreate, ModelUpdate
from workbench.services import models

router = APIRouter(tags=["models"], dependencies=[Depends(require_same_origin)])


@router.get("/providers/{provider_id}/models")
async def list_provider_models(
    provider_id: int,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
    enabled: bool | None = None,
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await models.list_models(
        provider_id=provider_id, enabled=enabled, limit=limit, cursor=decoded
    )
    return {"items": items, "nextCursor": next_cursor}


@router.post("/providers/{provider_id}/models", status_code=201)
async def create_model(provider_id: int, payload: ModelCreate) -> dict[str, object]:
    return await models.create_model(
        provider_id,
        model_name=payload.model_name,
        display_name=payload.display_name,
        default_temperature=(
            0.70 if payload.default_temperature is None else payload.default_temperature
        ),
        default_max_tokens=(
            4096 if payload.default_max_tokens is None else payload.default_max_tokens
        ),
        enabled=True if payload.enabled is None else payload.enabled,
    )


@router.get("/models")
async def list_models(
    provider_id: int | None = Query(None, alias="providerId"),
    enabled: bool | None = None,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await models.list_models(
        provider_id=provider_id, enabled=enabled, limit=limit, cursor=decoded
    )
    return {"items": items, "nextCursor": next_cursor}


@router.patch("/models/{model_id}")
async def update_model(model_id: int, payload: ModelUpdate) -> dict[str, object]:
    fields = payload.model_dump(exclude_unset=True)
    return await models.update_model(model_id, **fields)
