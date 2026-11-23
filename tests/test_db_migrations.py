"""迁移与双方言约束。用例名带 TC 编号。

本地默认 SQLite；设置 ``VIGIL_TEST_DATABASE_URL`` 时同一用例在 MySQL 复跑。
"""

from __future__ import annotations

import asyncio
import os
import sqlite3
import uuid

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import DBAPIError

from vigil_workbench.core.crypto import encrypt
from vigil_workbench.db.base import Base, utcnow
from vigil_workbench.db.engine import Database, create_engine_from_url
from vigil_workbench.db.models import (
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

HEAD = "0009"

# CHECK/唯一/FK 违反在 SQLite 与 MySQL 上的异常类型不一致：
# SQLite 抛 IntegrityError，MySQL 的 CHECK 违反（3819）抛 OperationalError。
# 统一按 DBAPIError 捕获，再用原始消息确认是约束违反而非任意数据库错误。
_CONSTRAINT_MARKERS = (
    "check constraint",
    "unique constraint",
    "duplicate entry",
    "foreign key constraint",
)


def _assert_constraint_violation(exc_info) -> None:  # noqa: ANN001
    orig = getattr(exc_info.value, "orig", exc_info.value)
    text = str(orig).lower()
    assert any(marker in text for marker in _CONSTRAINT_MARKERS), text


def _url(tmp_path) -> str:
    return os.environ.get(
        "VIGIL_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'migrated.db'}"
    )


def _alembic_config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


async def _drop_all_tables(url: str) -> None:
    """清空 schema（含 alembic 版本表），让用例从真正的空库开始。

    MySQL 是共享库，且 DDL 非事务：不能靠 ``downgrade base`` 兜底，否则
    downgrade 一旦失败就会留下半旧 schema 与残留数据；也不吞异常。
    """
    engine = create_engine_from_url(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    finally:
        await engine.dispose()


def _upgrade(url: str) -> None:
    asyncio.run(_drop_all_tables(url))
    command.upgrade(_alembic_config(url), "head")


def _test_name(prefix: str = "支付中心") -> str:
    """共享 MySQL 库下用唯一名，避免与历史残留数据撞唯一键。"""
    return f"{prefix}-{uuid.uuid4().hex}"


async def _constraint_scenario(url: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        sm = database.sessionmaker
        async with sm() as db:
            name = _test_name()
            project = ProjectContext(name=name, name_key=name)
            db.add(project)
            await db.commit()
            project_id = project.project_id

            db.add(ProjectContext(name=name, name_key=name))
            with pytest.raises(DBAPIError) as err:
                await db.commit()
            _assert_constraint_violation(err)
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
            with pytest.raises(DBAPIError) as err:
                await db.commit()
            _assert_constraint_violation(err)
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
            with pytest.raises(DBAPIError) as err:
                await db.commit()
            _assert_constraint_violation(err)
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

            with pytest.raises(DBAPIError) as err:
                await db.execute(delete(ProjectContext).where(ProjectContext.project_id == project_id))
                await db.commit()
            _assert_constraint_violation(err)
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


async def _insert_project_context(url: str, name: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        async with database.sessionmaker() as db:
            db.add(ProjectContext(name=name, name_key=name))
            await db.commit()
    finally:
        await database.dispose()


def _table_names(url: str) -> set[str]:
    tables, _version = asyncio.run(_assert_schema(url))
    return tables


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


def test_tc064_migration_order_and_knowledge_tables(tmp_path) -> None:
    url = _url(tmp_path)
    _upgrade(url)
    if not url.startswith("sqlite"):  # pragma: no cover - 仅 CI job 2
        return
    con = sqlite3.connect(tmp_path / "migrated.db")
    version = con.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert version == HEAD
    tables = {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"knowledge_base", "knowledge_entry"} <= tables
    con.close()


def test_tc064_downgrade_base_resets_shared_database(tmp_path) -> None:
    """downgrade 必须真正回到 base，才能在共享 MySQL 库上隔离各用例。

    回归：MySQL 不允许先删支撑外键的索引（错误 1553），旧 downgrade 因此在
    0005 处中断；_upgrade 又吞掉异常，导致 project_context 残留数据撞唯一键。
    """
    url = _url(tmp_path)
    name = _test_name("迁移隔离探针")

    _upgrade(url)
    asyncio.run(_insert_project_context(url, name))

    command.downgrade(_alembic_config(url), "base")
    assert "project_context" not in _table_names(url)

    command.upgrade(_alembic_config(url), "head")
    # 同名可再次插入，说明旧数据随 downgrade 一并清除。
    asyncio.run(_insert_project_context(url, name))


def test_tc064_migration_0006_injection_columns(tmp_path) -> None:
    """知识库导入/检索/失效判定/正文组装属 knowledge-base spec，本 spec 不重复。"""
    from pathlib import Path

    versions = Path("migrations/versions")
    names = {path.name for path in versions.glob("*.py") if path.name != "__init__.py"}
    assert any(name.startswith("0006") for name in names)

    url = _url(tmp_path)
    _upgrade(url)
    asyncio.run(_assert_injection_check(url))


async def _assert_injection_check(url: str) -> None:
    from vigil_workbench.core.crypto import encrypt
    from vigil_workbench.db.base import utcnow as now_fn

    database = Database(create_engine_from_url(url))
    try:
        sm = database.sessionmaker
        async with sm() as db:
            name = _test_name()
            project = ProjectContext(name=name, name_key=name)
            db.add(project)
            await db.flush()
            provider = ProviderConfig(
                name="OpenAI",
                protocol="openai_compatible",
                base_url="https://api.example.com/v1",
                api_key_ciphertext=encrypt("sk-test", key=bytes(range(32))),
            )
            db.add(provider)
            await db.flush()
            model = ModelBinding(
                provider_id=provider.provider_id,
                model_name="gpt-4.1",
                model_name_key="gpt-4.1",
                display_name="GPT-4.1",
            )
            db.add(model)
            await db.flush()
            now = now_fn()
            session = AnalysisSession(
                project_id=project.project_id,
                entrance_key="case-library",
                title="会话",
                status="in_progress",
                model_id=model.model_id,
                created_at=now,
                updated_at=now,
            )
            db.add(session)
            await db.commit()
            session_id = session.session_id
            model_id = model.model_id
            provider_id = provider.provider_id
            db.add(
                AiCallRecord(
                    session_id=session_id,
                    model_id=model_id,
                    provider_id=provider_id,
                    model_name_snapshot="gpt-4.1",
                    display_name_snapshot="GPT-4.1",
                    provider_name_snapshot="OpenAI",
                    protocol_snapshot="openai_compatible",
                    status="success",
                    prompt_digest="0" * 64,
                    prompt_preview="hi",
                    prompt_char_count=2,
                    injected_chars=1,
                    prompt_chars=2,
                    total_chars=9,
                    created_at=now,
                )
            )
            with pytest.raises(DBAPIError) as err:
                await db.commit()
            _assert_constraint_violation(err)
            await db.rollback()

            db.add(
                SessionEvent(
                    session_id=session_id,
                    type="knowledge_injection",
                    payload={"items": [], "promptChars": 0, "injectedChars": 0, "totalChars": 0},
                    created_at=now,
                )
            )
            await db.commit()
        async with database.engine.connect() as connection:
            tables = set(
                await connection.run_sync(lambda sync: inspect(sync).get_table_names())
            )
        assert "knowledge_base" in tables
    finally:
        await database.dispose()
