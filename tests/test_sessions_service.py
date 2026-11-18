"""会话与事件冻结签名。用例名带 TC 编号。"""

from __future__ import annotations

import inspect

import pytest
from sqlalchemy import func, select

from helpers import seed_model, seed_project, seed_provider, seed_session
from workbench.db.base import utcnow
from workbench.db.models import AnalysisSession, SessionEvent
from workbench.services import sessions
from workbench.services.errors import DomainError


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
