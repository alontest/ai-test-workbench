"""提供商服务：加密、掩码、连接测试与错误分类。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import time

import pytest
from sqlalchemy import func, select

from helpers import seed_provider
from workbench.adapters.ai.base import AdapterError, ConnectionTestResult
from workbench.core.crypto import decrypt
from workbench.db.models import AiCallRecord, Artifact, ProviderConfig, SessionEvent
from workbench.services import providers
from workbench.services.errors import DomainError

SECRET = "sk-test-key-1234"


class FakeConnectionAdapter:
    def __init__(self, *, result=None, error=None, delay=0.0):  # noqa: ANN001
        self.result = result
        self.error = error
        self.delay = delay

    async def test_connection(self, *, base_url, api_key, timeout=10):  # noqa: ANN001
        self.received = {"base_url": base_url, "api_key": api_key, "timeout": timeout}
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.result or ConnectionTestResult(True, 42, 7, None)

    async def complete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


async def _table_counts(sm) -> dict[str, int]:  # noqa: ANN001
    async with sm() as db:
        return {
            "sessions": 0,
            "events": await db.scalar(select(func.count()).select_from(SessionEvent)),
            "artifacts": await db.scalar(select(func.count()).select_from(Artifact)),
            "records": await db.scalar(select(func.count()).select_from(AiCallRecord)),
        }


@pytest.mark.asyncio
async def test_tc017_provider_key_encrypted_and_masked(database, settings) -> None:
    sm = database.sessionmaker
    view = await providers.create_provider(
        name="OpenAI",
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key=SECRET,
    )
    assert set(view) == {
        "providerId",
        "name",
        "protocol",
        "baseUrl",
        "apiKeyMasked",
        "enabled",
        "createdAt",
        "updatedAt",
    }
    assert "apiKey" not in view
    assert view["apiKeyMasked"] == "sk-****1234"
    assert view["enabled"] is True

    async with sm() as db:
        row = await db.get(ProviderConfig, view["providerId"])
        assert row.api_key_ciphertext.startswith("v1:")
        assert SECRET not in row.api_key_ciphertext
        assert decrypt(row.api_key_ciphertext, key=settings.encryption_key_bytes) == SECRET

    listing, _ = await providers.list_providers()
    assert listing[0]["apiKeyMasked"] == "sk-****1234"
    assert "apiKey" not in listing[0]


@pytest.mark.asyncio
async def test_tc018_provider_validation(database) -> None:
    sm = database.sessionmaker
    cases = [
        dict(name="", protocol="openai_compatible", base_url="https://x/v1", api_key="k"),
        dict(name="x", protocol="openai-compatible", base_url="https://x/v1", api_key="k"),
        dict(name="x", protocol="openai_compatible", base_url="ftp://x/v1", api_key="k"),
        dict(
            name="x",
            protocol="openai_compatible",
            base_url="https://user:pass@x/v1",
            api_key="k",
        ),
        dict(
            name="x",
            protocol="openai_compatible",
            base_url="https://" + "a" * 500,
            api_key="k",
        ),
        dict(name="x", protocol="openai_compatible", base_url="https://x/v1", api_key=""),
    ]
    for case in cases:
        with pytest.raises(DomainError) as err:
            await providers.create_provider(**case)
        assert err.value.status_code == 400
        assert err.value.details[0]["field"]

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(ProviderConfig)) == 0


@pytest.mark.asyncio
async def test_tc019_connection_test_timeout(database, settings) -> None:
    sm = database.sessionmaker
    provider_id = await seed_provider(sm)
    before = await _table_counts(sm)
    adapter = FakeConnectionAdapter(error=TimeoutError(), delay=10.1)

    started = time.monotonic()
    result = await providers.test_connection(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key=SECRET,
        provider_id=provider_id,
        adapter=adapter,
        timeout=0.05,
    )
    assert time.monotonic() - started < 2
    assert result["ok"] is False
    assert result["errorCode"] == "timeout"
    assert result["latencyMs"] >= 0
    assert await _table_counts(sm) == before


@pytest.mark.asyncio
async def test_tc020_disabled_provider_blocks_models(database) -> None:
    from workbench.services import models

    sm = database.sessionmaker
    provider_id = await seed_provider(sm)
    model_id = (
        await models.create_model(
            provider_id, model_name="gpt-4.1", display_name="GPT-4.1"
        )
    )["modelId"]

    await providers.update_provider(provider_id, enabled=False)
    enabled, _ = await models.list_models(enabled=True)
    assert enabled == []

    all_models, _ = await models.list_models()
    assert [item["modelId"] for item in all_models] == [model_id]
    async with sm() as db:
        from workbench.db.models import ModelBinding

        row = await db.get(ModelBinding, model_id)
        assert row.enabled is True

    await providers.update_provider(provider_id, enabled=True)
    enabled, _ = await models.list_models(enabled=True)
    assert [item["modelId"] for item in enabled] == [model_id]


@pytest.mark.asyncio
async def test_tc021_connection_test_error_codes(database, settings) -> None:
    sm = database.sessionmaker
    mapping = {
        "auth": AdapterError("auth", "upstream auth failed"),
        "rate_limit": AdapterError("rate_limit", "rate limited"),
        "server_error": AdapterError("server_error", "upstream 500"),
        "unreachable": AdapterError("unreachable", "connect failed"),
        "invalid_request": AdapterError("invalid_request", "bad request"),
    }
    for code, error in mapping.items():
        result = await providers.test_connection(
            protocol="anthropic",
            base_url="https://api.example.com/v1",
            api_key=SECRET,
            adapter=FakeConnectionAdapter(error=error),
        )
        assert result["ok"] is False
        assert result["errorCode"] == code
        assert SECRET not in str(result)

    corrupt = await seed_provider(sm, ciphertext="v1:%%%:%%%")
    result = await providers.test_connection(
        protocol="openai_compatible",
        base_url="https://api.example.com/v1",
        api_key=None,
        provider_id=corrupt,
        adapter=FakeConnectionAdapter(),
    )
    assert result["ok"] is False
    assert result["errorCode"] == "credential_unavailable"
    assert "%%%" not in str(result)


@pytest.mark.asyncio
async def test_tc022_update_key_blank_keeps(database, settings) -> None:
    sm = database.sessionmaker
    created = await providers.create_provider(
        name="OpenAI",
        protocol="openai_compatible",
        base_url="https://api.example.com/v1/",
        api_key=SECRET,
    )
    assert created["baseUrl"] == "https://api.example.com/v1"

    async with sm() as db:
        before = (await db.get(ProviderConfig, created["providerId"])).api_key_ciphertext

    omitted = await providers.update_provider(created["providerId"], name="OpenAI 2")
    assert omitted["name"] == "OpenAI 2"
    empty = await providers.update_provider(created["providerId"], api_key="")
    async with sm() as db:
        after = (await db.get(ProviderConfig, created["providerId"])).api_key_ciphertext
    assert after == before

    with pytest.raises(DomainError) as err:
        await providers.update_provider(created["providerId"], api_key="   ")
    assert err.value.details[0]["field"] == "apiKey"

    rotated = await providers.update_provider(
        created["providerId"], api_key="sk-test-qwerty"
    )
    async with sm() as db:
        rotated_cipher = (
            await db.get(ProviderConfig, created["providerId"])
        ).api_key_ciphertext
    assert rotated_cipher != before
    assert rotated["apiKeyMasked"] == "sk-****erty"
    assert (
        decrypt(rotated_cipher, key=settings.encryption_key_bytes) == "sk-test-qwerty"
    )


@pytest.mark.asyncio
async def test_tc050_credential_decrypt_failure_no_record(database, settings) -> None:
    sm = database.sessionmaker
    corrupt = await seed_provider(sm, ciphertext="v2:AAAA:BBBB")
    before = await _table_counts(sm)
    with pytest.raises(DomainError) as err:
        await providers.resolve_credentials(corrupt)
    assert err.value.code == "provider_credential_unavailable"
    assert err.value.status_code == 502
    assert "AAAA" not in str(err.value)
    assert await _table_counts(sm) == before
