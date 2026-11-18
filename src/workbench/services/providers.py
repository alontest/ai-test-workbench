"""提供商配置：AES-256-GCM 落库、掩码展示与连接测试。"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from workbench.adapters.ai.base import AdapterError, ProtocolAdapter, classify_error
from workbench.adapters.ai.anthropic import AnthropicAdapter
from workbench.adapters.ai.openai_compatible import OpenAICompatibleAdapter
from workbench.api.pagination import encode_cursor
from workbench.config import get_settings
from workbench.core.constants import CONNECTION_TEST_TIMEOUT_SECONDS
from workbench.core.crypto import CredentialUnavailable, decrypt, encrypt, mask_secret
from workbench.core.validation import optional_text, require_http_url, require_text
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.models import ProviderConfig
from workbench.db.repositories import providers as providers_repo
from workbench.services.errors import DomainError

UNSET: Any = object()
PROTOCOLS = ("openai_compatible", "anthropic")
_API_KEY_MAX = 512


def to_view(row: ProviderConfig, *, masked: str | None = None) -> dict[str, Any]:
    return {
        "providerId": row.provider_id,
        "name": row.name,
        "protocol": row.protocol,
        "baseUrl": row.base_url,
        "apiKeyMasked": masked if masked is not None else _mask(row),
        "enabled": row.enabled,
        "createdAt": row.created_at,
        "updatedAt": row.updated_at,
    }


def _mask(row: ProviderConfig) -> str:
    try:
        return mask_secret(decrypt(row.api_key_ciphertext))
    except CredentialUnavailable:
        return "****"


def _validate_protocol(protocol: str) -> str:
    if protocol not in PROTOCOLS:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "protocol", "message": "仅支持 openai_compatible 或 anthropic"}],
        )
    return protocol


def _validate_base_url(base_url: str) -> str:
    return require_http_url(base_url, field="baseUrl").rstrip("/")


def _validate_api_key(api_key: str, *, required: bool) -> str | None:
    if api_key == "" and not required:
        return None
    if not api_key.strip():
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "apiKey", "message": "密钥不能为空"}],
        )
    if len(api_key) > _API_KEY_MAX:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "apiKey", "message": f"长度不能超过 {_API_KEY_MAX}"}],
        )
    return api_key


async def create_provider(
    *, name: str, protocol: str, base_url: str, api_key: str
) -> dict[str, Any]:
    cleaned_name = require_text(name, field="name", max_length=100)
    cleaned_protocol = _validate_protocol(protocol)
    cleaned_url = _validate_base_url(base_url)
    cleaned_key = _validate_api_key(api_key, required=True)
    assert cleaned_key is not None
    now = utcnow()
    row = ProviderConfig(
        name=cleaned_name,
        protocol=cleaned_protocol,
        base_url=cleaned_url,
        api_key_ciphertext=encrypt(cleaned_key),
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return to_view(row)


async def get_provider(provider_id: int) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await providers_repo.get(db, provider_id)
        if row is None:
            raise _not_found()
        return to_view(row)


async def update_provider(
    provider_id: int,
    *,
    name: str | Any = UNSET,
    protocol: str | Any = UNSET,
    base_url: str | Any = UNSET,
    api_key: str | None | Any = UNSET,
    enabled: bool | Any = UNSET,
) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await providers_repo.get(db, provider_id)
        if row is None:
            raise _not_found()
        if name is not UNSET:
            row.name = require_text(name, field="name", max_length=100)
        if protocol is not UNSET:
            row.protocol = _validate_protocol(protocol)
        if base_url is not UNSET:
            row.base_url = _validate_base_url(base_url)
        if api_key is not UNSET and api_key not in (None, ""):
            cleaned = _validate_api_key(api_key, required=True)
            assert cleaned is not None
            row.api_key_ciphertext = encrypt(cleaned)
        if enabled is not UNSET:
            row.enabled = bool(enabled)
        row.updated_at = _bump(row.updated_at, utcnow())
        await db.commit()
        await db.refresh(row)
        return to_view(row)


async def list_providers(
    *, limit: int = 20, cursor: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], str | None]:
    after = _parse_cursor(cursor, "provider_id")
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        rows = await providers_repo.list_page(db, limit=limit + 1, after=after)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            {"updated_at": last.updated_at.isoformat(), "provider_id": last.provider_id}
        )
    return [to_view(row) for row in page], next_cursor


async def resolve_credentials(provider_id: int) -> tuple[str, str, str]:
    """返回 (protocol, base_url, 明文密钥)；解密失败不泄露密文。"""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await providers_repo.get(db, provider_id)
        if row is None:
            raise _not_found()
        protocol = row.protocol
        base_url = row.base_url
        ciphertext = row.api_key_ciphertext
    try:
        api_key = decrypt(ciphertext)
    except CredentialUnavailable as exc:
        raise DomainError(
            "provider_credential_unavailable",
            "提供商凭据不可用。",
            status_code=502,
            details=[{"field": "providerId", "message": "credential unavailable"}],
        ) from exc
    return protocol, base_url, api_key


async def test_connection(
    *,
    protocol: str,
    base_url: str,
    api_key: str | None,
    provider_id: int | None = None,
    adapter: ProtocolAdapter | None = None,
    timeout: float = CONNECTION_TEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """连接测试：独立超时、无副作用；上游失败仍返回 ok=false。"""
    if provider_id is not None and api_key in (None, ""):
        try:
            stored_protocol, stored_url, stored_key = await resolve_credentials(provider_id)
        except DomainError as exc:
            if exc.code != "provider_credential_unavailable":
                raise
            return _failure("credential_unavailable")
        protocol, base_url, api_key = stored_protocol, stored_url, stored_key
    else:
        protocol = _validate_protocol(protocol)
        base_url = _validate_base_url(base_url)
        _validate_api_key(api_key or "", required=True)

    client = adapter or _adapter_for(protocol)
    started = time.monotonic()
    try:
        async with asyncio.timeout(timeout):
            result = await client.test_connection(
                base_url=base_url, api_key=api_key or "", timeout=timeout
            )
    except (TimeoutError, asyncio.TimeoutError):
        return _failure("timeout", started)
    except AdapterError as exc:
        return _failure(exc.code, started)
    except Exception as exc:  # 网络/SDK 异常统一分类，不吞掉日志
        return _failure(classify_error(exc), started)
    latency = int((time.monotonic() - started) * 1000)
    return {
        "ok": bool(result.ok),
        "latencyMs": max(result.latency_ms, latency),
        "modelCount": result.model_count,
        "errorCode": result.error_code,
    }


def _adapter_for(protocol: str) -> ProtocolAdapter:
    if protocol == "anthropic":
        return AnthropicAdapter()
    return OpenAICompatibleAdapter()


def _failure(error_code: str, started: float | None = None) -> dict[str, Any]:
    latency = int((time.monotonic() - started) * 1000) if started is not None else 0
    return {"ok": False, "latencyMs": latency, "modelCount": None, "errorCode": error_code}


def _not_found() -> DomainError:
    return DomainError(
        "provider_not_found",
        "提供商不存在。",
        status_code=404,
        details=[{"field": "providerId", "message": "provider not found"}],
    )


def _bump(previous, now):  # noqa: ANN001, ANN202
    if now <= previous:
        return previous.replace(microsecond=min(previous.microsecond + 1, 999999))
    return now


def _parse_cursor(cursor: dict[str, Any] | None, id_key: str):  # noqa: ANN001, ANN202
    if cursor is None:
        return None
    from datetime import datetime as _dt

    raw_time = cursor.get("updated_at")
    raw_id = cursor.get(id_key)
    if not isinstance(raw_time, str) or not isinstance(raw_id, int):
        raise DomainError("validation_error", "游标非法。")
    moment = _dt.fromisoformat(raw_time.replace("Z", "+00:00")).replace(tzinfo=None)
    return moment, raw_id
