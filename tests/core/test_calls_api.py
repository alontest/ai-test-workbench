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
from vigil_workbench.adapters.ai.base import AdapterError
from vigil_workbench.db.models import AiCallRecord, SessionEvent
from vigil_workbench.services.ai_gateway import AiGateway
from vigil_workbench.services.errors import DomainError

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
KB_ID = "3f2504e04f8911d39a0c0305e82c3301"


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
    from vigil_workbench.db.models import AdminCredential

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
@pytest.mark.parametrize("blank_prompt", ["", "   ", "\n\t "])
async def test_tc043_blank_prompt_rejected_before_gateway(
    settings, database, blank_prompt
) -> None:
    """空/纯空白提示在接口层返回 400 validation_error，且不落到网关。"""
    fake = FakeAI()
    client = await _make(settings, database, fake)
    try:
        _project_id, _model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": blank_prompt},
            headers=ORIGIN,
        )
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert any(item.get("field") == "prompt" for item in body["details"])
        async with database.sessionmaker() as db:
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


@pytest.mark.asyncio
async def test_tc067_knowledge_injection_serialization(settings, database) -> None:
    import hashlib

    from sqlalchemy import text

    from vigil_workbench.core.redaction import redact
    from vigil_workbench.db.base import utcnow
    from vigil_workbench.db.models import KnowledgeBase, ModelBinding

    fake = FakeAI()
    client = await _make(settings, database, fake)
    try:
        project_id, model_id, session_id = await _session(database)
        items = [
            {
                "kbId": KB_ID,
                "kbName": "支付中心知识库",
                "kbVersion": 2,
                "entryCodes": ["ENT-012", "BR-003"],
                "injectedChars": 3,
            }
        ]
        async with database.sessionmaker() as db:
            model = await db.get(ModelBinding, model_id)
            assert model is not None
            now = utcnow()
            plain = AiCallRecord(
                session_id=session_id,
                model_id=model_id,
                provider_id=model.provider_id,
                model_name_snapshot=model.model_name,
                display_name_snapshot=model.display_name,
                provider_name_snapshot="OpenAI",
                protocol_snapshot="openai_compatible",
                status="success",
                prompt_digest=hashlib.sha256(b"plain").hexdigest(),
                prompt_preview=redact("plain", max_length=200),
                prompt_char_count=5,
                result_text="不应出现在列表",
                created_at=now,
                finished_at=now,
                latency_ms=10,
            )
            injected = AiCallRecord(
                session_id=session_id,
                model_id=model_id,
                provider_id=model.provider_id,
                model_name_snapshot=model.model_name,
                display_name_snapshot=model.display_name,
                provider_name_snapshot="OpenAI",
                protocol_snapshot="openai_compatible",
                status="success",
                prompt_digest=hashlib.sha256(b"injected").hexdigest(),
                prompt_preview=redact("injected", max_length=200),
                prompt_char_count=8,
                knowledge_injection=items,
                injected_chars=3,
                prompt_chars=5,
                total_chars=8,
                result_text="注入成功结果",
                created_at=now,
                finished_at=now,
                latency_ms=12,
            )
            db.add_all([plain, injected])
            await db.commit()
            plain_id, injected_id = plain.call_id, injected.call_id

        listed = await client.get("/api/v1/calls")
        assert listed.status_code == 200
        by_id = {item["callId"]: item for item in listed.json()["items"]}
        assert by_id[plain_id]["knowledgeInjection"] is None
        assert "resultText" not in by_id[plain_id]
        snapshot = by_id[injected_id]["knowledgeInjection"]
        assert snapshot[0]["kbId"] == KB_ID
        assert snapshot[0]["kbName"] == "支付中心知识库"
        assert snapshot[0]["kbVersion"] == 2
        assert snapshot[0]["entryCodes"] == ["ENT-012", "BR-003"]
        assert snapshot[0]["injectedChars"] == 3
        assert snapshot[0]["kbDeleted"] is True
        assert "resultText" not in by_id[injected_id]

        detail = await client.get(f"/api/v1/calls/{injected_id}")
        assert detail.status_code == 200
        assert detail.json()["resultText"] == "注入成功结果"
        assert detail.json()["knowledgeInjection"][0]["kbDeleted"] is True
        assert detail.json()["knowledgeInjection"][0]["kbName"] == "支付中心知识库"

        async with database.sessionmaker() as db:
            # knowledge_base 由迁移 0007 创建；这里只验证「行存在 / 不存在」。
            db.add(
                KnowledgeBase(
                    kb_id=KB_ID,
                    project_id=project_id,
                    name="支付中心知识库",
                    name_key="支付中心知识库",
                    version=2,
                    current_flag="1",
                    status="ready",
                    source_index_sha256="0" * 64,
                    storage_dir=f"knowledge-bases/{KB_ID}",
                )
            )
            await db.commit()

        present = await client.get(f"/api/v1/calls/{injected_id}")
        assert present.json()["knowledgeInjection"][0]["kbDeleted"] is False
        assert present.json()["knowledgeInjection"][0]["kbName"] == "支付中心知识库"

        async with database.sessionmaker() as db:
            await db.execute(
                text("DELETE FROM knowledge_base WHERE kb_id = :kb_id"),
                {"kb_id": KB_ID},
            )
            await db.commit()
        deleted = await client.get(f"/api/v1/calls/{injected_id}")
        assert deleted.json()["knowledgeInjection"][0]["kbDeleted"] is True
        assert deleted.json()["knowledgeInjection"][0]["kbName"] == "支付中心知识库"

        async with database.sessionmaker() as db:
            await db.execute(text("DROP TABLE knowledge_base"))
            await db.commit()
        dropped = await client.get("/api/v1/calls")
        dropped_item = next(
            item for item in dropped.json()["items"] if item["callId"] == injected_id
        )
        assert dropped_item["knowledgeInjection"][0]["kbDeleted"] is True
        assert dropped_item["knowledgeInjection"][0]["kbName"] == "支付中心知识库"
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
