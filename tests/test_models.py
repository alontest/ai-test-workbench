"""模型登记、参数范围与默认值。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from helpers import build_client, make_app, seed_admin, seed_provider, seed_session
from workbench.db.models import ModelBinding
from workbench.services import models
from workbench.services.ai_gateway import AiGateway
from workbench.services.errors import DomainError

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return "answer"

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_tc023_create_model_and_ranges(database) -> None:
    sm = database.sessionmaker
    provider_id = await seed_provider(sm)

    view = await models.create_model(
        provider_id, model_name="gpt-4.1", display_name="GPT-4.1"
    )
    assert set(view) == {
        "modelId",
        "providerId",
        "modelName",
        "displayName",
        "defaultTemperature",
        "defaultMaxTokens",
        "enabled",
        "createdAt",
    }
    assert view["defaultTemperature"] == pytest.approx(0.7)
    assert view["defaultMaxTokens"] == 4096

    enabled, _ = await models.list_models(enabled=True)
    assert [item["modelId"] for item in enabled] == [view["modelId"]]
    assert enabled[0]["provider"]["providerId"] == provider_id
    assert enabled[0]["provider"]["enabled"] is True

    for bad_temp in (-0.01, 2.01):
        with pytest.raises(DomainError) as err:
            await models.create_model(
                provider_id,
                model_name=f"m{bad_temp}",
                display_name="x",
                default_temperature=bad_temp,
            )
        assert err.value.details[0]["field"] == "defaultTemperature"

    for good_temp in (0, 2):
        created = await models.create_model(
            provider_id,
            model_name=f"temp-{good_temp}",
            display_name="x",
            default_temperature=good_temp,
        )
        assert created["defaultTemperature"] == pytest.approx(good_temp)

    for bad_tokens in (0, 1_000_001):
        with pytest.raises(DomainError) as err:
            await models.create_model(
                provider_id,
                model_name=f"tok-{bad_tokens}",
                display_name="x",
                default_max_tokens=bad_tokens,
            )
        assert err.value.details[0]["field"] == "defaultMaxTokens"

    for good_tokens in (1, 1_000_000):
        created = await models.create_model(
            provider_id,
            model_name=f"max-{good_tokens}",
            display_name="x",
            default_max_tokens=good_tokens,
        )
        assert created["defaultMaxTokens"] == good_tokens


@pytest.mark.asyncio
async def test_tc024_duplicate_model_name(database) -> None:
    sm = database.sessionmaker
    provider_id = await seed_provider(sm)
    other = await seed_provider(sm, name="Anthropic", protocol="anthropic")
    await models.create_model(provider_id, model_name="gpt-4.1", display_name="GPT-4.1")

    for duplicate in ("GPT-4.1", " gpt-4.1 "):
        with pytest.raises(DomainError) as err:
            await models.create_model(
                provider_id, model_name=duplicate, display_name="x"
            )
        assert err.value.code == "model_name_duplicate"
        assert err.value.status_code == 409
        assert err.value.details[0]["field"] == "modelName"

    allowed = await models.create_model(other, model_name="gpt-4.1", display_name="x")
    assert allowed["providerId"] == other


@pytest.mark.asyncio
async def test_tc025_default_params_used_and_override_not_persisted(database) -> None:
    sm = database.sessionmaker
    provider_id = await seed_provider(sm)
    created = await models.create_model(
        provider_id,
        model_name="gpt-4.1",
        display_name="GPT-4.1",
        default_temperature=0.7,
        default_max_tokens=1024,
    )
    model_id = created["modelId"]
    from helpers import seed_project

    project_id = await seed_project(sm)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    adapter = FakeAdapter()
    gateway = AiGateway(adapter=adapter, retry_backoff=0)
    await gateway.complete(session_id, model_id, "hi")
    assert adapter.calls[0]["temperature"] == pytest.approx(0.7)
    assert adapter.calls[0]["max_tokens"] == 1024

    await gateway.complete(session_id, model_id, "hi", temperature=0.2, max_tokens=2048)
    assert adapter.calls[1]["temperature"] == pytest.approx(0.2)
    assert adapter.calls[1]["max_tokens"] == 2048

    async with sm() as db:
        row = await db.get(ModelBinding, model_id)
        assert float(row.default_temperature) == pytest.approx(0.7)
        assert row.default_max_tokens == 1024


@pytest.mark.asyncio
async def test_tc023_api_models_crud(settings, database) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as client:
        await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        provider = (
            await client.post(
                "/api/v1/providers",
                json={
                    "name": "OpenAI",
                    "protocol": "openai_compatible",
                    "baseUrl": "https://api.example.com/v1",
                    "apiKey": "sk-test-key-1234",
                },
                headers=ORIGIN,
            )
        ).json()
        created = await client.post(
            f"/api/v1/providers/{provider['providerId']}/models",
            json={"modelName": "gpt-4.1", "displayName": "GPT-4.1"},
            headers=ORIGIN,
        )
        assert created.status_code == 201
        body = created.json()
        assert body["modelName"] == "gpt-4.1"

        duplicate = await client.post(
            f"/api/v1/providers/{provider['providerId']}/models",
            json={"modelName": "GPT-4.1", "displayName": "x"},
            headers=ORIGIN,
        )
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "model_name_duplicate"

        out_of_range = await client.post(
            f"/api/v1/providers/{provider['providerId']}/models",
            json={
                "modelName": "bad",
                "displayName": "x",
                "defaultTemperature": 2.5,
            },
            headers=ORIGIN,
        )
        assert out_of_range.status_code == 400
        assert out_of_range.json()["details"][0]["field"] == "defaultTemperature"

        listing = await client.get("/api/v1/models?enabled=true")
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert [item["modelId"] for item in items] == [body["modelId"]]
        assert items[0]["provider"]["name"] == "OpenAI"

        per_provider = await client.get(
            f"/api/v1/providers/{provider['providerId']}/models"
        )
        assert per_provider.status_code == 200
        assert len(per_provider.json()["items"]) == 1

        patched = await client.patch(
            f"/api/v1/models/{body['modelId']}",
            json={"enabled": False, "displayName": "GPT-4.1 mini"},
            headers=ORIGIN,
        )
        assert patched.status_code == 200
        assert patched.json()["enabled"] is False
        assert patched.json()["displayName"] == "GPT-4.1 mini"

        after = await client.get("/api/v1/models?enabled=true")
        assert after.json()["items"] == []

        missing = await client.post(
            "/api/v1/providers/999999/models",
            json={"modelName": "x", "displayName": "x"},
            headers=ORIGIN,
        )
        assert missing.status_code == 404
        assert missing.json()["code"] == "provider_not_found"
