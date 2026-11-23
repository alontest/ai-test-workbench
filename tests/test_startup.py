"""启动自检与 running 归并。用例名带 TC 编号。"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select, text

from helpers import seed_model, seed_project, seed_provider, seed_session
from vigil_workbench.core.constants import LOGIN_ATTEMPT_RETENTION, LOGIN_SESSION_RETENTION
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import (
    AiCallRecord,
    AnalysisSession,
    LoginAttempt,
    LoginSession,
    SessionEvent,
)
from vigil_workbench.services.sessions import append_event
from vigil_workbench.startup import HEAD_REVISION, merge_running_calls, run_startup


@pytest.mark.asyncio
async def test_tc049_startup_merges_running_calls(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    async with sm() as db:
        record = AiCallRecord(
            session_id=session_id,
            model_id=model_id,
            provider_id=provider_id,
            model_name_snapshot="gpt-4.1",
            display_name_snapshot="GPT-4.1",
            provider_name_snapshot="OpenAI",
            protocol_snapshot="openai_compatible",
            status="running",
            prompt_digest="0" * 64,
            prompt_preview="hi",
            prompt_char_count=2,
            created_at=utcnow() - timedelta(seconds=5),
        )
        db.add(record)
        await db.commit()
        call_id = record.call_id

    merged = await merge_running_calls(sm)
    assert merged == 1

    async with sm() as db:
        record = await db.get(AiCallRecord, call_id)
        assert record.status == "failed"
        assert record.error_code == "interrupted"
        assert record.finished_at is not None
        assert record.latency_ms is not None and record.latency_ms >= 5000
        event = await db.scalar(
            select(SessionEvent).where(SessionEvent.session_id == session_id)
        )
        assert event.type == "call"
        assert event.payload["errorCode"] == "interrupted"
        session = await db.get(AnalysisSession, session_id)
        assert session.status == "in_progress"


async def _seed_alembic_head(database) -> None:  # noqa: ANN001
    async with database.engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        await conn.execute(text("DELETE FROM alembic_version"))
        await conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:v)"),
            {"v": HEAD_REVISION},
        )


@pytest.mark.asyncio
async def test_tc049_restart_merges_running(database, settings) -> None:
    sm = database.sessionmaker
    await _seed_alembic_head(database)
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    now = utcnow()
    async with sm() as db:
        record = AiCallRecord(
            session_id=session_id,
            model_id=model_id,
            provider_id=provider_id,
            model_name_snapshot="gpt-4.1",
            display_name_snapshot="GPT-4.1",
            provider_name_snapshot="OpenAI",
            protocol_snapshot="openai_compatible",
            status="running",
            prompt_digest="1" * 64,
            prompt_preview="restart-me",
            prompt_char_count=10,
            created_at=now - timedelta(seconds=8),
        )
        db.add(record)
        db.add(
            LoginSession(
                token_hash="a" * 64,
                created_at=now - LOGIN_SESSION_RETENTION - timedelta(days=2),
                last_seen_at=now - LOGIN_SESSION_RETENTION - timedelta(days=1),
            )
        )
        db.add(
            LoginSession(
                token_hash="b" * 64,
                created_at=now,
                last_seen_at=now,
            )
        )
        db.add(
            LoginAttempt(
                source_ip_hash="c" * 64,
                failed_count=2,
                first_failed_at=now - LOGIN_ATTEMPT_RETENTION - timedelta(hours=2),
                last_failed_at=now - LOGIN_ATTEMPT_RETENTION - timedelta(hours=1),
            )
        )
        await db.commit()
        call_id = record.call_id

    await run_startup(database, settings)

    async with sm() as db:
        record = await db.get(AiCallRecord, call_id)
        assert record.status == "failed"
        assert record.error_code == "interrupted"
        assert record.finished_at is not None
        assert record.latency_ms is not None and record.latency_ms >= 8000
        events = (
            await db.scalars(
                select(SessionEvent)
                .where(SessionEvent.session_id == session_id)
                .order_by(SessionEvent.event_id)
            )
        ).all()
        assert any(event.type == "call" and event.payload.get("errorCode") == "interrupted" for event in events)
        session = await db.get(AnalysisSession, session_id)
        assert session.status == "in_progress"
        stale = await db.scalar(select(LoginSession).where(LoginSession.token_hash == "a" * 64))
        fresh = await db.scalar(select(LoginSession).where(LoginSession.token_hash == "b" * 64))
        attempt = await db.get(LoginAttempt, "c" * 64)
        assert stale is None
        assert fresh is not None
        assert attempt is None

    written = await append_event(
        session_id,
        "input_text",
        {"title": "继续排查", "text": "重启后仍可输入", "charCount": 8},
    )
    assert written["type"] == "input_text"
    assert written["payload"]["text"] == "重启后仍可输入"
