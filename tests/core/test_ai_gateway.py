"""AI 网关冻结签名、记录与超时重试。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import inspect

import pytest
from sqlalchemy import func, select

from helpers import seed_model, seed_project, seed_provider, seed_session
from vigil_workbench.adapters.ai.base import AdapterError
from vigil_workbench.db.models import AiCallRecord, SessionEvent
from vigil_workbench.services.ai_gateway import AIError, AIResult, AiGateway
from vigil_workbench.services.errors import DomainError


class FakeAdapter:
    def __init__(self, *, text: str = "模型回答", errors: list[Exception] | None = None, delay: float = 0.0):
        self.text = text
        self.errors = list(errors or [])
        self.delay = delay
        self.calls: list[dict] = []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.errors:
            raise self.errors.pop(0)
        return self.text

    async def test_connection(self, **kwargs):  # pragma: no cover - 网关不使用
        raise NotImplementedError


def test_tc057_frozen_gateway_signature() -> None:
    sig = inspect.signature(AiGateway.complete)
    assert list(sig.parameters) == [
        "self",
        "session_id",
        "model_id",
        "prepared",
        "temperature",
        "max_tokens",
        "injection",
    ]
    assert sig.parameters["temperature"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["max_tokens"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["injection"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["injection"].default is None

    assert set(AIResult.__dataclass_fields__) == {
        "call_id",
        "text",
        "status",
        "latency_ms",
        "retry_count",
        "model_id",
        "model_display_name",
        "knowledge_injection",
    }


@pytest.mark.asyncio
async def test_tc041_success_records_call(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    adapter = FakeAdapter(text="hello from model")
    gateway = AiGateway(adapter=adapter)
    result = await gateway.complete(session_id, model_id, "你好", temperature=0.2, max_tokens=100)
    assert result.text == "hello from model"
    assert result.status == "success"
    assert result.model_id == model_id
    assert result.retry_count == 0
    assert result.latency_ms >= 0
    assert adapter.calls[0]["prepared"] == "你好"
    assert adapter.calls[0]["temperature"] == pytest.approx(0.2)
    assert adapter.calls[0]["max_tokens"] == 100

    async with sm() as db:
        record = await db.get(AiCallRecord, result.call_id)
        assert record.status == "success"
        assert record.result_text == "hello from model"
        assert record.finished_at is not None
        assert record.total_chars == len("你好")
        assert record.prompt_chars == len("你好")
        events = (
            await db.scalars(select(SessionEvent).where(SessionEvent.session_id == session_id))
        ).all()
        assert [e.type for e in events] == ["call"]
        assert events[0].payload["callId"] == result.call_id
        assert events[0].payload["status"] == "success"


@pytest.mark.asyncio
async def test_tc042_upstream_failure_recorded(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    gateway = AiGateway(adapter=FakeAdapter(errors=[AdapterError("auth", "bad key")]))
    with pytest.raises(AIError) as err:
        await gateway.complete(session_id, model_id, "hi")
    assert err.value.code == "auth"
    assert err.value.call_id > 0

    async with sm() as db:
        record = await db.get(AiCallRecord, err.value.call_id)
        assert record.status == "failed"
        assert record.error_code == "auth"
        assert record.finished_at is not None
        event = await db.scalar(select(SessionEvent))
        assert event.payload["errorCode"] == "auth"


@pytest.mark.asyncio
async def test_tc045_retry_then_timeout(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    adapter = FakeAdapter(errors=[AdapterError("server_error", "500")], text="ok after retry")
    gateway = AiGateway(adapter=adapter, retry_backoff=0)
    result = await gateway.complete(session_id, model_id, "hi")
    assert result.retry_count == 1
    assert result.text == "ok after retry"
    assert len(adapter.calls) == 2

    timeout_gateway = AiGateway(adapter=FakeAdapter(delay=0.2), attempt_timeout=0.05)
    with pytest.raises(AIError) as err:
        await timeout_gateway.complete(session_id, model_id, "hi")
    assert err.value.code == "timeout"
    assert err.value.retry_count == 0

    async with sm() as db:
        timeout_record = await db.get(AiCallRecord, err.value.call_id)
        assert timeout_record.status == "timeout"
        assert timeout_record.error_code == "timeout"


@pytest.mark.asyncio
async def test_tc045_cancellation_finalizes_record(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    queued_session_id = await seed_session(
        sm, project_id=project_id, model_id=model_id, title="排队会话"
    )

    entered = asyncio.Event()
    release = asyncio.Event()

    class HoldingAdapter:
        calls = 0

        async def complete(self, **kwargs):  # noqa: ANN003, ANN201
            HoldingAdapter.calls += 1
            entered.set()
            await release.wait()
            return "should-not-return"

        async def test_connection(self, **kwargs):  # pragma: no cover
            raise NotImplementedError

    gateway = AiGateway(adapter=HoldingAdapter())
    gateway._semaphore = asyncio.Semaphore(1)

    running = asyncio.create_task(gateway.complete(session_id, model_id, "first"))
    await entered.wait()
    queued = asyncio.create_task(gateway.complete(queued_session_id, model_id, "queued"))
    await asyncio.sleep(0.05)

    async with sm() as db:
        running_count = await db.scalar(
            select(func.count()).select_from(AiCallRecord).where(AiCallRecord.status == "running")
        )
        total_count = await db.scalar(select(func.count()).select_from(AiCallRecord))
    assert running_count == 1
    assert total_count == 1
    assert HoldingAdapter.calls == 1

    running.cancel()
    with pytest.raises(asyncio.CancelledError):
        await running
    release.set()
    queued_result = await queued
    assert queued_result.status == "success"
    assert queued_result.latency_ms < 500

    async with sm() as db:
        interrupted = await db.scalar(
            select(AiCallRecord).where(AiCallRecord.session_id == session_id)
        )
        queued_record = await db.get(AiCallRecord, queued_result.call_id)
        assert interrupted is not None
        assert interrupted.status == "failed"
        assert interrupted.error_code == "interrupted"
        assert interrupted.finished_at is not None
        assert interrupted.latency_ms is not None
        assert queued_record.status == "success"
        event = await db.scalar(
            select(SessionEvent).where(
                SessionEvent.session_id == session_id, SessionEvent.type == "call"
            )
        )
        assert event.payload["errorCode"] == "interrupted"
        assert event.payload["status"] == "failed"


@pytest.mark.asyncio
async def test_tc041_preconditions_create_no_record(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    gateway = AiGateway(adapter=FakeAdapter())

    with pytest.raises(DomainError) as err:
        await gateway.complete(session_id, model_id, "x" * (settings.prompt_max_chars + 1))
    assert err.value.code == "prompt_too_long"

    closed_id = await seed_session(
        sm, project_id=project_id, model_id=model_id, status="completed"
    )
    with pytest.raises(DomainError) as err:
        await gateway.complete(closed_id, model_id, "hi")
    assert err.value.code == "session_closed"

    broken_provider = await seed_provider(sm, name="Broken", ciphertext="v1:bad:bad")
    broken_model = await seed_model(sm, broken_provider, model_name="broken")
    with pytest.raises(DomainError) as err:
        await gateway.complete(session_id, broken_model, "hi")
    assert err.value.code == "provider_credential_unavailable"

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == 0
