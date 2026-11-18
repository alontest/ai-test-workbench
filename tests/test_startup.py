"""启动自检与 running 归并。用例名带 TC 编号。"""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from helpers import seed_model, seed_project, seed_provider, seed_session
from workbench.db.base import utcnow
from workbench.db.models import AiCallRecord, AnalysisSession, SessionEvent
from workbench.startup import merge_running_calls


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
