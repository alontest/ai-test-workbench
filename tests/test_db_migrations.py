"""迁移与双方言约束。用例名带 TC 编号。

本地默认 SQLite；设置 ``AW_TEST_DATABASE_URL`` 时同一用例在 MySQL 复跑。
"""

from __future__ import annotations

import asyncio
import os
import sqlite3

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from workbench.core.crypto import encrypt
from workbench.db.base import utcnow
from workbench.db.engine import Database, create_engine_from_url
from workbench.db.models import (
    AiCallRecord,
    AnalysisSession,
    Artifact,
    ModelBinding,
    ProjectContext,
    ProviderConfig,
    SessionEvent,
)

EXPECTED_TABLES = {
    "admin_credential",
    "login_session",
    "login_attempt",
    "project_context",
    "provider_config",
    "model_binding",
    "analysis_session",
    "session_event",
    "artifact",
    "ai_call_record",
}

HEAD = "0006"


def _url(tmp_path) -> str:
    return os.environ.get(
        "AW_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}"
    )


def _upgrade(url: str) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    try:
        command.downgrade(config, "base")
    except Exception:
        pass
    command.upgrade(config, "head")


async def _constraint_scenario(url: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        sm = database.sessionmaker
        async with sm() as db:
            project = ProjectContext(name="支付中心", name_key="支付中心")
            db.add(project)
            await db.commit()
            project_id = project.project_id

            db.add(ProjectContext(name="支付中心", name_key="支付中心"))
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()

            provider = ProviderConfig(
                name="OpenAI",
                protocol="openai_compatible",
                base_url="https://api.example.com/v1",
                api_key_ciphertext=encrypt("sk-test", key=bytes(range(32))),
            )
            db.add(provider)
            await db.commit()
            provider_id = provider.provider_id

            db.add(
                ProviderConfig(
                    name="Bad",
                    protocol="openai-compatible",
                    base_url="https://api.example.com/v1",
                    api_key_ciphertext=encrypt("sk-test", key=bytes(range(32))),
                )
            )
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()

            model = ModelBinding(
                provider_id=provider_id,
                model_name="gpt-4.1",
                model_name_key="gpt-4.1",
                display_name="GPT-4.1",
            )
            db.add(model)
            await db.commit()
            model_id = model.model_id

            now = utcnow()
            session = AnalysisSession(
                project_id=project_id,
                entrance_key="case-library",
                title="会话",
                status="in_progress",
                model_id=model_id,
                created_at=now,
                updated_at=now,
            )
            db.add(session)
            await db.commit()
            session_id = session.session_id

            db.add(
                AnalysisSession(
                    project_id=project_id,
                    entrance_key="unknown",
                    title="bad",
                    model_id=model_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            with pytest.raises(IntegrityError):
                await db.commit()
            await db.rollback()

            db.add(
                SessionEvent(
                    session_id=session_id,
                    type="knowledge_injection",
                    payload={"items": []},
                    created_at=now,
                )
            )
            db.add(
                Artifact(
                    session_id=session_id,
                    kind="upload",
                    file_name="app.log",
                    file_name_key="app.log",
                    storage_name="abc.log",
                    relative_path=f"sessions/{session_id}/abc.log",
                    mime_type="text/plain",
                    byte_size=0,
                    created_at=now,
                )
            )
            db.add(
                AiCallRecord(
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
                    created_at=now,
                )
            )
            await db.commit()

            with pytest.raises(IntegrityError):
                await db.execute(delete(ProjectContext).where(ProjectContext.project_id == project_id))
                await db.commit()
            await db.rollback()

            await db.execute(delete(AnalysisSession).where(AnalysisSession.session_id == session_id))
            await db.commit()
            for model_cls in (SessionEvent, Artifact, AiCallRecord):
                count = await db.scalar(select(func.count()).select_from(model_cls))
                assert count == 0
            assert await db.scalar(select(func.count()).select_from(ProjectContext)) == 1
    finally:
        await database.dispose()


async def _assert_schema(url: str) -> tuple[set[str], str]:
    engine = create_engine_from_url(url)
    try:
        async with engine.connect() as connection:
            tables = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))
            version = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    finally:
        await engine.dispose()
    return tables, str(version)


def test_tc058_migrate_empty_db_to_head(tmp_path) -> None:
    url = _url(tmp_path)
    _upgrade(url)
    tables, version = asyncio.run(_assert_schema(url))
    assert EXPECTED_TABLES <= tables
    assert version == HEAD
    if url.startswith("sqlite"):
        con = sqlite3.connect(tmp_path / "migrated.db")
        tables = {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert EXPECTED_TABLES <= tables
        assert con.execute("SELECT version_num FROM alembic_version").fetchone() == (HEAD,)
        columns = {row[1] for row in con.execute("PRAGMA table_info(ai_call_record)")}
        assert {"knowledge_injection", "injected_chars", "prompt_chars", "total_chars"} <= columns
        con.close()


def test_tc059_constraints_on_test_database(tmp_path) -> None:
    url = _url(tmp_path)
    _upgrade(url)
    asyncio.run(_constraint_scenario(url))


def test_tc064_migration_order_and_no_knowledge_table(tmp_path) -> None:
    url = _url(tmp_path)
    _upgrade(url)
    if not url.startswith("sqlite"):  # pragma: no cover - 仅 CI job 2
        return
    con = sqlite3.connect(tmp_path / "migrated.db")
    version = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == "0006"
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "knowledge_base" not in tables
    con.close()
