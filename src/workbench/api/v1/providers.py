"""提供商接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from workbench.api.deps import require_same_origin
from workbench.api.pagination import decode_cursor
from workbench.api.schemas.provider import (
    ConnectionTestRequest,
    ProviderCreate,
    ProviderUpdate,
)
from workbench.services import providers

router = APIRouter(
    prefix="/providers",
    tags=["providers"],
    dependencies=[Depends(require_same_origin)],
)


@router.get("")
async def list_providers(
    limit: int = Query(20, ge=1, le=100), cursor: str | None = None
) -> dict[str, object]:
    decoded = decode_cursor(cursor) if cursor else None
    items, next_cursor = await providers.list_providers(limit=limit, cursor=decoded)
    return {"items": items, "nextCursor": next_cursor}


@router.post("", status_code=201)
async def create_provider(payload: ProviderCreate) -> dict[str, object]:
    return await providers.create_provider(
        name=payload.name,
        protocol=payload.protocol,
        base_url=payload.base_url,
        api_key=payload.api_key,
    )


@router.post("/connection-test")
async def connection_test_unsaved(
    payload: ConnectionTestRequest,
) -> dict[str, object]:
    return await providers.test_connection(
        protocol=payload.protocol or "",
        base_url=payload.base_url or "",
        api_key=payload.api_key,
    )


@router.get("/{provider_id}")
async def get_provider(provider_id: int) -> dict[str, object]:
    return await providers.get_provider(provider_id)


@router.patch("/{provider_id}")
async def update_provider(
    provider_id: int, payload: ProviderUpdate
) -> dict[str, object]:
    fields = payload.model_dump(exclude_unset=True)
    return await providers.update_provider(provider_id, **fields)


@router.post("/{provider_id}/connection-test")
async def connection_test_saved(
    provider_id: int, payload: ConnectionTestRequest | None = None
) -> dict[str, object]:
    body = payload or ConnectionTestRequest()
    return await providers.test_connection(
        protocol=body.protocol or "",
        base_url=body.base_url or "",
        api_key=body.api_key,
        provider_id=provider_id,
    )
