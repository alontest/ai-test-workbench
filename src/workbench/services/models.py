"""模型绑定：登记、参数范围与可选列表。"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy.exc import DBAPIError

from workbench.api.pagination import encode_cursor
from workbench.core.validation import require_text
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.errors import is_unique_violation
from workbench.db.models import ModelBinding, ProviderConfig
from workbench.db.repositories import models as models_repo
from workbench.db.repositories import providers as providers_repo
from workbench.services.errors import DomainError

UNSET: Any = object()
_NAME_MAX = 191
_TWO_PLACES = Decimal("0.01")


def to_view(row: ModelBinding, provider: ProviderConfig | None = None) -> dict[str, Any]:
    view: dict[str, Any] = {
        "modelId": row.model_id,
        "providerId": row.provider_id,
        "modelName": row.model_name,
        "displayName": row.display_name,
        "defaultTemperature": float(row.default_temperature),
        "defaultMaxTokens": row.default_max_tokens,
        "enabled": row.enabled,
        "createdAt": row.created_at,
    }
    if provider is not None:
        view["provider"] = {
            "providerId": provider.provider_id,
            "name": provider.name,
            "enabled": provider.enabled,
        }
    return view


def _validate_temperature(value: float | Decimal) -> Decimal:
    try:
        temperature = Decimal(str(value))
    except Exception as exc:  # noqa: BLE001 - 非法输入统一转 400
        raise _invalid("defaultTemperature", "温度必须是 0–2 的数字") from exc
    if temperature < 0 or temperature > 2:
        raise _invalid("defaultTemperature", "温度必须为 0–2")
    return temperature.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _validate_max_tokens(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 1_000_000:
        raise _invalid("defaultMaxTokens", "最大 token 必须为 1–1,000,000")
    return value


def _invalid(field: str, message: str) -> DomainError:
    return DomainError(
        "validation_error", "请求参数校验失败。", details=[{"field": field, "message": message}]
    )


def _duplicate() -> DomainError:
    return DomainError(
        "model_name_duplicate",
        "同一提供商下模型名称已存在。",
        status_code=409,
        details=[{"field": "modelName", "message": "模型名称已存在"}],
    )


async def create_model(
    provider_id: int,
    *,
    model_name: str,
    display_name: str,
    default_temperature: float | Decimal = 0.70,
    default_max_tokens: int = 4096,
    enabled: bool = True,
) -> dict[str, Any]:
    cleaned_name = require_text(model_name, field="modelName", max_length=_NAME_MAX)
    cleaned_display = require_text(display_name, field="displayName", max_length=_NAME_MAX)
    temperature = _validate_temperature(default_temperature)
    max_tokens = _validate_max_tokens(default_max_tokens)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        provider = await providers_repo.get(db, provider_id)
        if provider is None:
            raise DomainError(
                "provider_not_found",
                "提供商不存在。",
                status_code=404,
                details=[{"field": "providerId", "message": "provider not found"}],
            )
        key = cleaned_name.casefold()
        if await models_repo.get_by_name_key(db, provider_id, key) is not None:
            raise _duplicate()
        row = ModelBinding(
            provider_id=provider_id,
            model_name=cleaned_name,
            model_name_key=key,
            display_name=cleaned_display,
            default_temperature=temperature,
            default_max_tokens=max_tokens,
            enabled=enabled,
            created_at=utcnow(),
        )
        db.add(row)
        try:
            await db.commit()
        except DBAPIError as exc:
            await db.rollback()
            if is_unique_violation(exc):
                raise _duplicate() from exc
            raise
        await db.refresh(row)
        return to_view(row)


async def get_model(model_id: int) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await models_repo.get(db, model_id)
        if row is None:
            raise _not_found()
        provider = await providers_repo.get(db, row.provider_id)
        assert provider is not None
        return to_view(row, provider)


async def update_model(
    model_id: int,
    *,
    display_name: str | Any = UNSET,
    default_temperature: float | Decimal | Any = UNSET,
    default_max_tokens: int | Any = UNSET,
    enabled: bool | Any = UNSET,
) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await models_repo.get(db, model_id)
        if row is None:
            raise _not_found()
        if display_name is not UNSET:
            row.display_name = require_text(
                display_name, field="displayName", max_length=_NAME_MAX
            )
        if default_temperature is not UNSET:
            row.default_temperature = _validate_temperature(default_temperature)
        if default_max_tokens is not UNSET:
            row.default_max_tokens = _validate_max_tokens(default_max_tokens)
        if enabled is not UNSET:
            row.enabled = bool(enabled)
        await db.commit()
        await db.refresh(row)
        return to_view(row)


async def list_models(
    *,
    provider_id: int | None = None,
    enabled: bool | None = None,
    limit: int = 20,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    after = _parse_cursor(cursor)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        rows = await models_repo.list_page(
            db,
            limit=limit + 1,
            provider_id=provider_id,
            enabled_only=enabled is True,
            after=after,
        )
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        last, _ = page[-1]
        next_cursor = encode_cursor(
            {"created_at": last.created_at.isoformat(), "model_id": last.model_id}
        )
    return [to_view(row, provider) for row, provider in page], next_cursor


def _not_found() -> DomainError:
    return DomainError(
        "model_not_found",
        "模型不存在。",
        status_code=404,
        details=[{"field": "modelId", "message": "model not found"}],
    )


def _parse_cursor(cursor: dict[str, Any] | None):  # noqa: ANN001, ANN202
    if cursor is None:
        return None
    from datetime import datetime as _dt

    raw_time = cursor.get("created_at")
    raw_id = cursor.get("model_id")
    if not isinstance(raw_time, str) or not isinstance(raw_id, int):
        raise DomainError("validation_error", "游标非法。")
    moment = _dt.fromisoformat(raw_time.replace("Z", "+00:00")).replace(tzinfo=None)
    return moment, raw_id
