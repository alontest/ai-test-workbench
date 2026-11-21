"""唯一调用入口 /ai/complete 的知识库引用。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from fake_preparer import KB_ID, ScriptedInjectionPreparer
from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
    seed_session,
)
from workbench.core.ports import register_injection_preparer
from workbench.db.models import AiCallRecord, SessionEvent
from workbench.services.ai_gateway import AiGateway

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}

INVALID_ITEM = {"kbId": KB_ID, "code": "ENT-009", "reason": "superseded"}


class FakeAI:
    def __init__(self, *, text: str = "模型回答") -> None:
        self.text = text
        self.calls: list[dict] = []

    async def complete(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        return self.text

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


_counter = iter(range(1000))


async def _session(database) -> tuple[int, int, int]:  # noqa: ANN001
    index = next(_counter)
    sm = database.sessionmaker
    project_id = await seed_project(sm, name=f"项目{index}")
    provider_id = await seed_provider(sm, name=f"Provider {index}")
    model_id = await seed_model(sm, provider_id, model_name=f"gpt-4.1-{index}")
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    return project_id, model_id, session_id


async def _client(settings, database, fake: FakeAI, preparer=None):  # noqa: ANN001
    from workbench.db.models import AdminCredential

    async with database.sessionmaker() as db:
        exists = await db.get(AdminCredential, 1) is not None
    if not exists:
        await seed_admin(database.sessionmaker, ADMIN)
    if preparer is not None:
        register_injection_preparer(preparer)
    gateway = AiGateway(adapter=fake, retry_backoff=0)
    app = make_app(settings, database, ai_gateway=gateway)
    client = build_client(app)
    await client.__aenter__()
    await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
    return client


async def _assert_no_record(database, fake: FakeAI) -> None:  # noqa: ANN001
    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == 0
    assert fake.calls == []


@pytest.mark.asyncio
async def test_tc068_invalid_entries_require_confirmation(settings, database) -> None:
    fake = FakeAI()
    preparer = ScriptedInjectionPreparer()
    preparer.invalid_items = [INVALID_ITEM]
    client = await _client(settings, database, fake, preparer)
    try:
        project_id, _model_id, session_id = await _session(database)
        payload = {
            "prompt": "请分析",
            "knowledgeRefs": [{"kbId": KB_ID, "entryCodes": ["ENT-012", "BR-003"]}],
        }
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json=payload,
            headers=ORIGIN,
        )
        assert response.status_code == 409
        body = response.json()
        assert body["code"] == "knowledge_invalid_entries"
        assert body["details"]["invalidItems"] == [INVALID_ITEM]
        await _assert_no_record(database, fake)
        assert len(preparer.calls) == 1
        assert preparer.calls[0]["session_id"] == session_id
        assert preparer.calls[0]["project_id"] == project_id
        assert preparer.calls[0]["prompt"] == "请分析"

        partial = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={
                **payload,
                "confirmInvalidCodes": [{"kbId": KB_ID, "code": "ENT-000"}],
            },
            headers=ORIGIN,
        )
        assert partial.status_code == 409
        assert partial.json()["code"] == "knowledge_invalid_entries"
        assert partial.json()["details"]["invalidItems"] == [INVALID_ITEM]
        await _assert_no_record(database, fake)
        assert len(preparer.calls) == 2
    finally:
        register_injection_preparer(None)
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc069_confirmed_injection_and_limits(settings, database) -> None:
    fake = FakeAI(text="ok")
    preparer = ScriptedInjectionPreparer()
    preparer.invalid_items = [INVALID_ITEM]
    client = await _client(settings, database, fake, preparer)
    try:
        _project_id, _model_id, session_id = await _session(database)
        payload = {
            "prompt": "请分析",
            "knowledgeRefs": [{"kbId": KB_ID, "entryCodes": ["ENT-012", "BR-003"]}],
            "confirmInvalidCodes": [{"kbId": KB_ID, "code": "ENT-009"}],
        }
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json=payload,
            headers=ORIGIN,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["knowledgeInjection"]
        assert body["knowledgeInjection"][0]["kbId"] == KB_ID
        assert body["knowledgeInjection"][0]["kbName"] == "支付中心知识库"
        assert "kbDeleted" in body["knowledgeInjection"][0]
        assert fake.calls[0]["prepared"] == preparer.prepared

        async with database.sessionmaker() as db:
            record = await db.get(AiCallRecord, body["callId"])
            assert record is not None
            assert isinstance(record.knowledge_injection, list)
            assert record.injected_chars == 3
            assert record.prompt_chars == 3
            assert record.total_chars == 6
            events = list(
                await db.scalars(
                    select(SessionEvent).where(SessionEvent.session_id == session_id)
                )
            )
            assert "knowledge_injection" in [event.type for event in events]
    finally:
        register_injection_preparer(None)
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc069_empty_set_and_budget_and_unavailable(settings, database) -> None:
    fake = FakeAI()
    preparer = ScriptedInjectionPreparer()
    preparer.empty_after_confirm = True
    client = await _client(settings, database, fake, preparer)
    try:
        _project_id, _model_id, session_id = await _session(database)
        refs = {"knowledgeRefs": [{"kbId": KB_ID, "entryCodes": ["ENT-012"]}]}
        empty = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "请分析", **refs},
            headers=ORIGIN,
        )
        assert empty.status_code == 409
        assert empty.json()["code"] == "knowledge_injection_empty"
        await _assert_no_record(database, fake)

        preparer.empty_after_confirm = False
        preparer.budget = {
            "prompt_chars": 3,
            "injected_chars": 199_998,
            "total_chars": 200_001,
            "limit": 200_000,
        }
        budget = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "请分析", **refs},
            headers=ORIGIN,
        )
        assert budget.status_code == 400
        assert budget.json()["code"] == "prompt_budget_exceeded"
        details = budget.json()["details"]
        assert details == {
            "promptChars": 3,
            "injectedChars": 199_998,
            "totalChars": 200_001,
            "limit": 200_000,
        }
        await _assert_no_record(database, fake)
    finally:
        register_injection_preparer(None)
        await client.__aexit__(None, None, None)

    missing = FakeAI()
    client = await _client(settings, database, missing, preparer=None)
    try:
        _project_id, _model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={
                "prompt": "请分析",
                "knowledgeRefs": [{"kbId": KB_ID, "entryCodes": ["ENT-012"]}],
            },
            headers=ORIGIN,
        )
        assert response.status_code == 409
        assert response.json()["code"] == "knowledge_unavailable"
        async with database.sessionmaker() as db:
            # 上一个用例已清零；本会话也不得留下记录
            assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
        assert missing.calls == []

        baseline = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "请分析"},
            headers=ORIGIN,
        )
        assert baseline.status_code == 200
        assert baseline.json()["knowledgeInjection"] is None
        assert missing.calls[0]["prepared"] == "请分析"
    finally:
        await client.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_tc069_omitted_refs_do_not_touch_preparer(settings, database) -> None:
    fake = FakeAI(text="ok")
    preparer = ScriptedInjectionPreparer()
    preparer.invalid_items = [INVALID_ITEM]
    client = await _client(settings, database, fake, preparer)
    try:
        _project_id, _model_id, session_id = await _session(database)
        response = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "你好"},
            headers=ORIGIN,
        )
        assert response.status_code == 200
        assert response.json()["knowledgeInjection"] is None
        assert preparer.calls == []
        assert fake.calls[0]["prepared"] == "你好"
    finally:
        register_injection_preparer(None)
        await client.__aexit__(None, None, None)
