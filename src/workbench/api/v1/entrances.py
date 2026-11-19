"""入口配置接口：6 入口唯一来源。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from workbench.api.deps import require_same_origin
from workbench.core.entrances import entrance_to_dict, get_entrance, iter_entrances
from workbench.services.errors import DomainError

router = APIRouter(
    prefix="/entrances", tags=["entrances"], dependencies=[Depends(require_same_origin)]
)


@router.get("")
async def list_entrances() -> dict[str, object]:
    return {"items": [entrance_to_dict(item) for item in iter_entrances()]}


@router.get("/{key}")
async def get_entrance_item(key: str) -> dict[str, str]:
    item = get_entrance(key)
    if item is None:
        raise DomainError(
            "entrance_unknown",
            "未知入口。",
            details=[{"field": "key", "message": key}],
        )
    return entrance_to_dict(item)
