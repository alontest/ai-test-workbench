"""会话与事件冻结签名。用例名带 TC 编号。"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select

from helpers import (
    seed_model,
    seed_project,
    seed_provider,
    seed_session,
    seed_session_graph,
)
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import AnalysisSession, SessionEvent
from vigil_workbench.services import sessions
from vigil_workbench.services.errors import DomainError


def test_tc057_frozen_session_signatures() -> None:
    create_sig = inspect.signature(sessions.create)
    assert list(create_sig.parameters) == ["project_id", "entrance_key", "title", "model_id"]
    assert all(
        p.kind is inspect.Parameter.KEYWORD_ONLY for p in create_sig.parameters.values()
    )

    append_sig = inspect.signature(sessions.append_event)
    assert list(append_sig.parameters) == ["session_id", "event_type", "payload", "actor"]
    assert append_sig.parameters["session_id"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert append_sig.parameters["actor"].kind is inspect.Parameter.KEYWORD_ONLY
    assert append_sig.parameters["actor"].default == "local-user"


@pytest.mark.asyncio
async def test_tc026_create_session_contract(database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)

    view = await sessions.create(
        project_id=project_id,
        entrance_key="case-library",
        title="  排查一次失败  ",
        model_id=model_id,
    )
    assert set(view) == {
        "session_id",
        "project_id",
        "entrance_key",
        "title",
        "status",
        "model_id",
        "created_at",
        "updated_at",
        "closed_at",
    }
    assert view["title"] == "排查一次失败"
    assert view["status"] == "in_progress"
    assert view["closed_at"] is None

    async def expect(code: str, **kwargs) -> None:
        before = await _session_count(sm)
        with pytest.raises(DomainError) as err:
            await sessions.create(**kwargs)
        assert err.value.code == code
        assert await _session_count(sm) == before

    await expect(
        "project_not_found",
        project_id=999999,
        entrance_key="case-library",
        title="x",
        model_id=model_id,
    )
    await expect(
        "model_not_found",
        project_id=project_id,
        entrance_key="case-library",
        title="x",
        model_id=999999,
    )
    await expect(
        "validation_error",
        project_id=project_id,
        entrance_key="case-library",
        title="",
        model_id=model_id,
    )
    await expect(
        "validation_error",
        project_id=project_id,
        entrance_key="case-library",
        title="x" * 201,
        model_id=model_id,
    )
    await expect(
        "validation_error",
        project_id=project_id,
        entrance_key="unknown",
        title="x",
        model_id=model_id,
    )

    disabled_model = await seed_model(sm, provider_id, model_name="disabled", enabled=False)
    await expect(
        "model_disabled",
        project_id=project_id,
        entrance_key="case-library",
        title="x",
        model_id=disabled_model,
    )

    disabled_provider = await seed_provider(sm, name="Disabled", enabled=False)
    model_under_disabled = await seed_model(
        sm, disabled_provider, model_name="m2", display_name="M2"
    )
    await expect(
        "provider_disabled",
        project_id=project_id,
        entrance_key="case-library",
        title="x",
        model_id=model_under_disabled,
    )


@pytest.mark.asyncio
async def test_tc057_append_event_contract(database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    async with sm() as db:
        before = await db.get(AnalysisSession, session_id)
        before_updated = before.updated_at

    event = await sessions.append_event(
        session_id,
        "input_text",
        {"title": "日志", "text": "boom", "charCount": 4},
    )
    assert set(event) == {"event_id", "session_id", "type", "payload", "created_at"}
    assert event["type"] == "input_text"
    assert event["payload"]["text"] == "boom"

    async with sm() as db:
        refreshed = await db.get(AnalysisSession, session_id)
        assert refreshed.updated_at > before_updated

    with pytest.raises(DomainError) as err:
        await sessions.append_event(session_id, "input_text", {"title": "x"})
    assert err.value.code == "validation_error"

    with pytest.raises(DomainError) as err:
        await sessions.append_event(session_id, "unknown", {})
    assert err.value.code == "validation_error"

    terminal_id = await seed_session(
        sm, project_id=project_id, model_id=model_id, status="completed"
    )
    with pytest.raises(DomainError) as err:
        await sessions.append_event(terminal_id, "input_text", {"title": "x", "text": "y", "charCount": 1})
    assert err.value.code == "session_closed"

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == 1
        assert await db.get(AnalysisSession, terminal_id) is not None


async def _session_count(sessionmaker) -> int:
    async with sessionmaker() as db:
        return await db.scalar(select(func.count()).select_from(AnalysisSession))


@pytest.mark.asyncio
async def test_tc027_list_filters(database) -> None:
    sm = database.sessionmaker
    project_a = await seed_project(sm, name="项目A")
    project_b = await seed_project(sm, name="项目B")
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)

    a1 = await seed_session(sm, project_id=project_a, model_id=model_id, title="a1")
    a2 = await seed_session(sm, project_id=project_a, model_id=model_id, title="a2")
    b1 = await seed_session(sm, project_id=project_b, model_id=model_id, title="b1")
    await sessions.complete_session(a2)

    items, _ = await sessions.list_sessions(project_id=project_a)
    assert {item["sessionId"] for item in items} == {a1, a2}

    completed, _ = await sessions.list_sessions(status="completed")
    assert [item["sessionId"] for item in completed] == [a2]

    first, cursor = await sessions.list_sessions(limit=2)
    assert len(first) == 2 and cursor is not None
    from vigil_workbench.api.pagination import decode_cursor

    second, second_cursor = await sessions.list_sessions(
        limit=2, cursor=decode_cursor(cursor)
    )
    assert len(second) == 1 and second_cursor is None
    assert not {item["sessionId"] for item in first} & {
        item["sessionId"] for item in second
    }
    assert {item["sessionId"] for item in first + second} == {a1, a2, b1}

    empty, next_cursor = await sessions.list_sessions(status="failed")
    assert empty == [] and next_cursor is None


@pytest.mark.asyncio
async def test_tc028_timeline_order(database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    await sessions.append_event(
        session_id, "input_text", {"title": "t", "text": "boom", "charCount": 4}
    )
    await sessions.append_event(
        session_id,
        "artifact",
        {
            "artifactId": 1,
            "fileName": "a.log",
            "byteSize": 3,
            "mimeType": "text/plain",
            "kind": "upload",
        },
    )
    await sessions.append_event(
        session_id,
        "call",
        {
            "callId": 1,
            "modelId": model_id,
            "modelDisplayName": "GPT",
            "status": "success",
            "latencyMs": 5,
            "retryCount": 0,
            "promptPreview": "boom",
            "errorCode": None,
        },
    )
    await sessions.append_event(
        session_id,
        "status_change",
        {"from": "in_progress", "to": "completed", "actor": "local-user", "at": "2026-11-18T00:00:00Z"},
    )

    page, cursor = await sessions.list_events_page(session_id, limit=2)
    assert [event["type"] for event in page] == ["input_text", "artifact"]
    assert cursor is not None
    from vigil_workbench.api.pagination import decode_cursor

    page2, cursor2 = await sessions.list_events_page(
        session_id, limit=2, cursor=decode_cursor(cursor)
    )
    assert [event["type"] for event in page2] == ["call", "status_change"]
    assert cursor2 is None

    empty_session = await seed_session(
        sm, project_id=project_id, model_id=model_id, title="empty"
    )
    assert await sessions.list_events_page(empty_session) == ([], None)


@pytest.mark.asyncio
async def test_tc029_terminal_state_rejects(database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    completed = await sessions.complete_session(session_id)
    assert completed["status"] == "completed"
    assert completed["closed_at"] is not None

    async with sm() as db:
        event = await db.scalar(
            select(SessionEvent).where(SessionEvent.session_id == session_id)
        )
        assert event.type == "status_change"
        assert event.payload["actor"] == "local-user"
        assert event.payload["to"] == "completed"

    with pytest.raises(DomainError) as err:
        await sessions.complete_session(session_id)
    assert err.value.code == "session_closed"
    assert err.value.status_code == 409

    with pytest.raises(DomainError) as err:
        await sessions.append_text_input(session_id, title="t", text="text")
    assert err.value.code == "session_closed"

    failing = await seed_session(
        sm, project_id=project_id, model_id=model_id, title="fail"
    )
    assert await sessions.fail_session(failing) is True
    async with sm() as db:
        row = await db.get(AnalysisSession, failing)
        assert row.status == "failed"
        event = await db.scalar(
            select(SessionEvent).where(SessionEvent.session_id == failing)
        )
        assert event.payload["actor"] == "system"
        assert event.payload["reason"] == "unhandled error"

    assert await sessions.fail_session(failing) is False


@pytest.mark.asyncio
async def test_tc030_delete_cascades(database, settings) -> None:
    from vigil_workbench.adapters.fs import storage
    from vigil_workbench.db.models import AiCallRecord, Artifact
    from vigil_workbench.services import artifacts

    sm = database.sessionmaker
    project_id, model_id, session_id = await seed_session_graph(sm)
    other_id = await seed_session(
        sm, project_id=project_id, model_id=model_id, title="保留"
    )

    import io

    await artifacts.save(session_id, file_name="a.log", source=io.BytesIO(b"a"))
    await artifacts.save(session_id, file_name="b.log", source=io.BytesIO(b"b"))
    async with sm() as db:
        db.add(
            AiCallRecord(
                session_id=session_id,
                model_id=model_id,
                provider_id=1,
                model_name_snapshot="gpt-4.1",
                display_name_snapshot="GPT",
                provider_name_snapshot="OpenAI",
                protocol_snapshot="openai_compatible",
                status="success",
                prompt_digest="0" * 64,
                prompt_preview="x",
                prompt_char_count=1,
                total_chars=1,
                prompt_chars=1,
            )
        )
        await db.commit()

    await sessions.delete_session(session_id)
    async with sm() as db:
        assert await db.get(AnalysisSession, session_id) is None
        assert await db.scalar(select(func.count()).select_from(SessionEvent).where(SessionEvent.session_id == session_id)) == 0
        assert await db.scalar(select(func.count()).select_from(Artifact).where(Artifact.session_id == session_id)) == 0
        assert await db.scalar(select(func.count()).select_from(AiCallRecord).where(AiCallRecord.session_id == session_id)) == 0
        assert await db.get(AnalysisSession, other_id) is not None
    assert not storage.artifact_dir(session_id).exists()

    with pytest.raises(DomainError) as err:
        await sessions.delete_session(session_id)
    assert err.value.code == "session_not_found"
