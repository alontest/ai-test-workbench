"""调用接口：成功、失败留痕、前置拒绝与重试。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
    seed_session,
    seed_session_graph,
)
from workbench.adapters.ai.base import AdapterError
from workbench.db.models import AiCallRecord, SessionEvent
from workbench.services.ai_gateway import AiGateway
from workbench.services.errors import DomainError

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


class FakeAI:
    def __init__(self, *, text="模型回答", errors=None, delay=0.0):  # noqa: ANN001
        self.text = text
        self.errors = list(errors or [])
        self.delay = delay
        self.calls: list[dict] = []

    async def complete(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.errors:
            error = self.errors.pop(0)
            if error is not None:
                raise error
        return self.text

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


async def _make(settings, database, fake: FakeAI, *, attempt_timeout: float = 120):
    from workbench.db.models import AdminCredential

    async with database.sessionmaker() as db:
        exists = await db.get(AdminCredential, 1) is not None
    if not exists:
        await seed_admin(database.sessionmaker, ADMIN)
    gateway = AiGateway(
        adapter=fake, attempt_timeout=attempt_timeout, retry_backoff=0
    )
    app = make_app(settings, database, ai_gateway=gateway)
    client = build_client(app)
    await client.__aenter__()
    await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
    return client


@pytest.mark.asyncio
async def test_tc041_api_call_success(settings, database) -> None:
    fake = FakeAI(text="hello from model")
    client = await _make(settings, database, fake)
    try:
        project_id, model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "你好"},
            headers=ORIGIN,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["resultText"] == "hello from model"
        assert body["status"] == "success"
        assert body["retryCount"] == 0
        assert body["callId"] > 0
        assert body["latencyMs"] >= 0
        assert body["model"]["modelId"] == model_id
        assert body["model"]["providerId"] > 0
        assert body["knowledgeInjection"] is None

        async with database.sessionmaker() as db:
            record = await db.get(AiCallRecord, body["callId"])
            assert record.status == "success"
            assert record.result_text == "hello from model"
            events = list(await db.scalars(select(SessionEvent)))
            assert [event.type for event in events] == ["call"]
            assert events[0].payload["callId"] == body["callId"]
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter_code", "expected_code", "expected_status", "occurrences"),
    [
        ("auth", "ai_auth", 502, 1),
        ("rate_limit", "ai_rate_limit", 502, 1),
        ("server_error", "ai_server_error", 502, 2),
        ("invalid_request", "ai_invalid_request", 502, 1),
    ],
)
async def test_tc042_api_call_failure(
    settings, database, adapter_code, expected_code, expected_status, occurrences
) -> None:
    fake = FakeAI(errors=[AdapterError(adapter_code, "upstream")] * occurrences)
    client = await _make(settings, database, fake)
    try:
        project_id, model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "你好"},
            headers=ORIGIN,
        )
        assert response.status_code == expected_status
        body = response.json()
        assert body["code"] == expected_code
        details = body["details"][0]
        assert details["callId"] > 0
        assert details["retryCount"] == (1 if adapter_code == "server_error" else 0)

        async with database.sessionmaker() as db:
            record = await db.get(AiCallRecord, details["callId"])
            assert record.status == "failed"
            assert record.error_code == adapter_code
            assert record.error_message
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc043_precondition_rejections_no_record(settings, database) -> None:
    fake = FakeAI()
    client = await _make(settings, database, fake)
    try:
        sm = database.sessionmaker
        project_id, model_id, session_id = await _session(database)
        closed = await seed_session(
            sm, project_id=project_id, model_id=model_id, status="completed"
        )
        disabled_model = await seed_model(sm, 1, model_name="off", enabled=False)
        disabled_provider = await seed_provider(sm, name="Off", enabled=False)
        under_disabled = await seed_model(
            sm, disabled_provider, model_name="m-off", display_name="M"
        )

        cases = [
            (999999, {"prompt": "x"}, 404, "session_not_found"),
            (closed, {"prompt": "x"}, 409, "session_closed"),
            (session_id, {"prompt": "x" * 200_001}, 400, "prompt_too_long"),
        ]
        for target, payload, status, code in cases:
            response = await client.post(
                f"/api/v1/sessions/{target}/ai/complete",
                json=payload,
                headers=ORIGIN,
            )
            assert response.status_code == status
            assert response.json()["code"] == code

        disabled = await seed_session(
            sm, project_id=project_id, model_id=disabled_model
        )
        response = await client.post(
            f"/api/v1/sessions/{disabled}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "model_disabled"

        off = await seed_session(
            sm, project_id=project_id, model_id=under_disabled
        )
        response = await client.post(
            f"/api/v1/sessions/{off}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "provider_disabled"

        async with sm() as db:
            assert (
                await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
            )
        assert fake.calls == []
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc044_call_event_payload(settings, database) -> None:
    fake = FakeAI(text="ok")
    client = await _make(settings, database, fake)
    try:
        project_id, model_id, session_id = await _session(database)
        prompt = "Authorization: Bearer sk-very-secret-token " + "x" * 500
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": prompt},
            headers=ORIGIN,
        )
        assert response.status_code == 200

        events = (
            await client.get(f"/api/v1/sessions/{session_id}/events")
        ).json()["items"]
        call = next(event for event in events if event["type"] == "call")
        payload = call["payload"]
        assert payload["modelId"] == model_id
        assert payload["modelDisplayName"] == "GPT-4.1"
        assert payload["status"] == "success"
        assert payload["latencyMs"] >= 0
        assert payload["retryCount"] == 0
        assert "sk-very-secret-token" not in payload["promptPreview"]
        assert len(payload["promptPreview"]) <= 200
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc045_api_retry_and_timeout(settings, database) -> None:
    fake = FakeAI(errors=[AdapterError("server_error", "boom")])
    client = await _make(settings, database, fake)
    try:
        project_id, model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 200
        assert response.json()["retryCount"] == 1
        assert len(fake.calls) == 2
    finally:
        await client.__aexit__(None, None, None)

    failing = FakeAI(
        errors=[AdapterError("server_error", "boom"), AdapterError("server_error", "boom")]
    )
    client = await _make(settings, database, failing)
    try:
        project_id, model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 502
        assert response.json()["code"] == "ai_server_error"
        assert response.json()["details"][0]["retryCount"] == 1
        assert len(failing.calls) == 2
    finally:
        await client.__aexit__(None, None, None)

    slow = FakeAI(delay=1.0)
    client = await _make(settings, database, slow, attempt_timeout=0.05)
    try:
        project_id, model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 504
        assert response.json()["code"] == "ai_timeout"
        details = response.json()["details"][0]
        assert details["retryCount"] == 0
        async with database.sessionmaker() as db:
            record = await db.get(AiCallRecord, details["callId"])
            assert record.status == "timeout"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc050_api_credential_unavailable(settings, database) -> None:
    fake = FakeAI()
    client = await _make(settings, database, fake)
    try:
        sm = database.sessionmaker
        project_id = await seed_project(sm)
        provider_id = await seed_provider(sm, ciphertext="v1:bad:bad")
        model_id = await seed_model(sm, provider_id)
        session_id = await seed_session(
            sm, project_id=project_id, model_id=model_id
        )
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "x"},
            headers=ORIGIN,
        )
        assert response.status_code == 502
        assert response.json()["code"] == "provider_credential_unavailable"
        async with sm() as db:
            assert (
                await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
            )
        assert fake.calls == []
    finally:
        await client.__aexit__(None, None, None)


_counter = iter(range(1000))


async def _session(database):  # noqa: ANN001
    index = next(_counter)
    sm = database.sessionmaker
    project_id = await seed_project(sm, name=f"项目{index}")
    provider_id = await seed_provider(sm, name=f"Provider {index}")
    model_id = await seed_model(
        sm, provider_id, model_name=f"gpt-4.1-{index}", display_name="GPT-4.1"
    )
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    return project_id, model_id, session_id
