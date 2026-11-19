"""网关注入留痕：TC-065 / TC-066。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select

from helpers import seed_model, seed_project, seed_provider, seed_session
from workbench.adapters.ai.base import AdapterError
from workbench.db.models import AiCallRecord, SessionEvent
from workbench.services.ai_gateway import (
    AIError,
    AiGateway,
    InjectionItem,
    InjectionSnapshot,
)
from workbench.services.errors import DomainError


class FakeAdapter:
    def __init__(
        self, *, text: str = "模型回答", errors: list[Exception] | None = None, delay: float = 0.0
    ):
        self.text = text
        self.errors = list(errors or [])
        self.delay = delay
        self.calls: list[dict] = []

    async def complete(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.errors:
            raise self.errors.pop(0)
        return self.text

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


def _snapshot(
    *,
    prompt: str,
    injected: str = "知识块",
    excluded: tuple[str, ...] = (),
) -> tuple[InjectionSnapshot, str]:
    prepared = injected + prompt
    item = InjectionItem(
        kb_id=5,
        kb_name="支付中心知识库",
        kb_version=2,
        entry_codes=("ENT-012", "BR-003"),
        injected_chars=len(injected),
    )
    snapshot = InjectionSnapshot(
        items=(item,),
        prompt_chars=len(prompt),
        injected_chars=len(injected),
        total_chars=len(prepared),
        excluded_codes=excluded,
    )
    return snapshot, prepared


async def _seed(sm) -> tuple[int, int]:  # noqa: ANN001
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    return session_id, model_id


def _assert_no_injection_columns(record: AiCallRecord, prepared: str) -> None:
    assert record.knowledge_injection is None
    assert record.injected_chars == 0
    assert record.prompt_chars == len(prepared)
    assert record.total_chars == len(prepared)
    assert record.prompt_char_count == len(prepared)


@pytest.mark.asyncio
async def test_tc065_no_injection_preserves_baseline(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    prepared = "你好"
    adapter = FakeAdapter(text="hello from model")
    gateway = AiGateway(adapter=adapter)

    result = await gateway.complete(session_id, model_id, prepared)
    assert result.text == "hello from model"
    assert result.status == "success"
    assert result.retry_count == 0
    assert result.knowledge_injection is None

    async with sm() as db:
        record = await db.get(AiCallRecord, result.call_id)
        assert record is not None
        _assert_no_injection_columns(record, prepared)
        events = list(
            await db.scalars(select(SessionEvent).where(SessionEvent.session_id == session_id))
        )
        assert [event.type for event in events] == ["call"]
        assert events[0].payload["callId"] == result.call_id
        assert events[0].payload["status"] == "success"


@pytest.mark.asyncio
async def test_tc065_no_injection_failure_and_timeout_have_no_event(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    prepared = "x"

    gateway = AiGateway(
        adapter=FakeAdapter(errors=[AdapterError("auth", "bad")]), retry_backoff=0
    )
    with pytest.raises(AIError):
        await gateway.complete(session_id, model_id, prepared)

    timeout_gateway = AiGateway(adapter=FakeAdapter(delay=0.2), attempt_timeout=0.05)
    with pytest.raises(AIError):
        await timeout_gateway.complete(session_id, model_id, prepared)

    async with sm() as db:
        records = list(await db.scalars(select(AiCallRecord)))
        assert len(records) == 2
        for record in records:
            _assert_no_injection_columns(record, prepared)
        events = list(await db.scalars(select(SessionEvent)))
        assert all(event.type == "call" for event in events)
        assert not any(event.type == "knowledge_injection" for event in events)


@pytest.mark.asyncio
async def test_tc066_injection_persisted_and_survives_failure(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    snapshot, prepared = _snapshot(prompt="请分析", excluded=("ENT-009",))
    adapter = FakeAdapter(text="ok")
    gateway = AiGateway(adapter=adapter, retry_backoff=0)

    result = await gateway.complete(session_id, model_id, prepared, injection=snapshot)
    assert result.status == "success"
    assert result.knowledge_injection == snapshot.items
    assert adapter.calls[0]["prepared"] == prepared

    async with sm() as db:
        record = await db.get(AiCallRecord, result.call_id)
        assert record is not None
        assert record.injected_chars == snapshot.injected_chars
        assert record.prompt_chars == snapshot.prompt_chars
        assert record.total_chars == snapshot.total_chars
        assert record.prompt_char_count == len(prepared)
        assert isinstance(record.knowledge_injection, list)
        assert record.knowledge_injection == [
            {
                "kbId": 5,
                "kbName": "支付中心知识库",
                "kbVersion": 2,
                "entryCodes": ["ENT-012", "BR-003"],
                "injectedChars": snapshot.injected_chars,
            }
        ]
        events = list(
            await db.scalars(
                select(SessionEvent)
                .where(SessionEvent.session_id == session_id)
                .order_by(SessionEvent.event_id)
            )
        )
        assert [event.type for event in events] == ["knowledge_injection", "call"]
        payload = events[0].payload
        assert payload["items"] == record.knowledge_injection
        assert payload["promptChars"] == snapshot.prompt_chars
        assert payload["injectedChars"] == snapshot.injected_chars
        assert payload["totalChars"] == snapshot.total_chars
        assert payload["excludedCodes"] == ["ENT-009"]
        assert "body" not in payload
        assert "text" not in payload


@pytest.mark.asyncio
async def test_tc066_injection_survives_upstream_failure_and_timeout(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    snapshot, prepared = _snapshot(prompt="失败路径")

    failing = FakeAdapter(
        errors=[AdapterError("server_error", "500"), AdapterError("server_error", "500")]
    )
    gateway = AiGateway(adapter=failing, retry_backoff=0)
    with pytest.raises(AIError) as err:
        await gateway.complete(session_id, model_id, prepared, injection=snapshot)
    assert err.value.code == "server_error"

    timeout_gateway = AiGateway(adapter=FakeAdapter(delay=0.2), attempt_timeout=0.05)
    with pytest.raises(AIError) as timeout_err:
        await timeout_gateway.complete(session_id, model_id, prepared, injection=snapshot)
    assert timeout_err.value.code == "timeout"

    async with sm() as db:
        failed = await db.get(AiCallRecord, err.value.call_id)
        timed_out = await db.get(AiCallRecord, timeout_err.value.call_id)
        assert failed is not None and timed_out is not None
        assert failed.status == "failed"
        assert timed_out.status == "timeout"
        for record in (failed, timed_out):
            assert record.knowledge_injection is not None
            assert record.injected_chars == snapshot.injected_chars
            assert record.total_chars == snapshot.total_chars
        injection_events = list(
            await db.scalars(
                select(SessionEvent).where(SessionEvent.type == "knowledge_injection")
            )
        )
        assert len(injection_events) == 2


@pytest.mark.asyncio
async def test_tc066_mismatch_rejects_without_record_or_request(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    adapter = FakeAdapter()
    gateway = AiGateway(adapter=adapter)
    item = InjectionItem(
        kb_id=5,
        kb_name="支付中心知识库",
        kb_version=2,
        entry_codes=("ENT-012",),
        injected_chars=3,
    )
    bad = InjectionSnapshot(
        items=(item,),
        prompt_chars=2,
        injected_chars=99,
        total_chars=5,
    )
    with pytest.raises(DomainError) as err:
        await gateway.complete(session_id, model_id, "abxxx", injection=bad)
    assert err.value.code == "injection_snapshot_mismatch"
    assert adapter.calls == []
    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == 0


@pytest.mark.asyncio
async def test_tc066_empty_items_and_cancel_keep_trace(database, settings) -> None:
    sm = database.sessionmaker
    session_id, model_id = await _seed(sm)
    prepared = "only-prompt"
    empty = InjectionSnapshot(
        items=(),
        prompt_chars=len(prepared),
        injected_chars=0,
        total_chars=len(prepared),
    )
    gateway = AiGateway(adapter=FakeAdapter(text="ok"))
    result = await gateway.complete(session_id, model_id, prepared, injection=empty)
    assert result.status == "success"

    entered = asyncio.Event()
    release = asyncio.Event()

    class HoldingAdapter:
        async def complete(self, **kwargs):  # noqa: ANN003, ANN201
            entered.set()
            await release.wait()
            return "nope"

        async def test_connection(self, **kwargs):  # pragma: no cover
            raise NotImplementedError

    snapshot, injected_prepared = _snapshot(prompt="cancel")
    holding = AiGateway(adapter=HoldingAdapter())
    task = asyncio.create_task(
        holding.complete(session_id, model_id, injected_prepared, injection=snapshot)
    )
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    release.set()

    async with sm() as db:
        empty_record = await db.get(AiCallRecord, result.call_id)
        assert empty_record is not None
        assert empty_record.knowledge_injection == []
        assert empty_record.injected_chars == 0
        cancelled = await db.scalar(
            select(AiCallRecord).where(AiCallRecord.call_id != result.call_id)
        )
        assert cancelled is not None
        assert cancelled.status == "failed"
        assert cancelled.error_code == "interrupted"
        assert cancelled.knowledge_injection is not None
        assert cancelled.injected_chars == snapshot.injected_chars
        assert (
            await db.scalar(
                select(func.count())
                .select_from(SessionEvent)
                .where(SessionEvent.type == "knowledge_injection")
            )
            == 2
        )
