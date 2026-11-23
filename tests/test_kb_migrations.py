"""迁移 0007：SQLite 默认，设置 AW_TEST_DATABASE_URL 时在 MySQL 复跑。"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import DBAPIError

from workbench.db.base import Base, utcnow
from workbench.db.engine import Database, create_engine_from_url
from workbench.db.models import KnowledgeBase, KnowledgeEntry, ProjectContext

CORE_TABLES = {
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
KB_TABLES = {"knowledge_base", "knowledge_entry"}
CONSTRAINT_MARKERS = (
    "check constraint",
    "unique constraint",
    "duplicate entry",
    "foreign key constraint",
)


def _url(tmp_path) -> str:
    return os.environ.get(
        "AW_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'kb_migrated.db'}"
    )


def _config(url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", url)
    return config


async def _reset(url: str) -> None:
    engine = create_engine_from_url(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    finally:
        await engine.dispose()


def _upgrade(url: str) -> None:
    asyncio.run(_reset(url))
    command.upgrade(_config(url), "0007")


async def _snapshot(url: str) -> dict[str, Any]:
    engine = create_engine_from_url(url)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(_inspect_sync)
    finally:
        await engine.dispose()


def _inspect_sync(connection) -> dict[str, Any]:  # noqa: ANN001
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    result: dict[str, Any] = {
        "tables": tables,
        "version": str(
            connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        ),
        "indexes": {},
        "uniques": {},
        "checks": {},
        "columns": {},
    }
    for table in KB_TABLES & tables:
        result["indexes"][table] = {
            item["name"] for item in inspector.get_indexes(table)
        }
        result["uniques"][table] = {
            item["name"] for item in inspector.get_unique_constraints(table)
        }
        result["checks"][table] = {
            item["name"] for item in inspector.get_check_constraints(table)
        }
    for table in {"ai_call_record", "project_context"} & tables:
        result["columns"][table] = {
            item["name"] for item in inspector.get_columns(table)
        }
    return result


def _assert_constraint_violation(exc_info) -> None:  # noqa: ANN001
    orig = getattr(exc_info.value, "orig", exc_info.value)
    text_ = str(orig).lower()
    assert any(marker in text_ for marker in CONSTRAINT_MARKERS), text_


async def _cascade_scenario(url: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        async with database.sessionmaker() as db:
            name = f"知识库迁移-{uuid.uuid4().hex}"
            project = ProjectContext(name=name, name_key=name)
            db.add(project)
            await db.flush()

            kb_id = uuid.uuid4().hex
            db.add(
                KnowledgeBase(
                    kb_id=kb_id,
                    project_id=project.project_id,
                    name=name,
                    name_key=name,
                    version=1,
                    current_flag="1",
                    status="ready",
                    entry_count=1,
                    file_count=1,
                    total_byte_size=10,
                    source_index_sha256="0" * 64,
                    storage_dir=f"knowledge-bases/{kb_id}",
                    created_at=utcnow(),
                    updated_at=utcnow(),
                )
            )
            db.add(
                KnowledgeEntry(
                    entry_id=uuid.uuid4().hex,
                    kb_id=kb_id,
                    code="ENT-1",
                    code_key="ent-1",
                    type="entity",
                    title="订单",
                    summary="订单摘要",
                    body="订单正文",
                    body_missing=False,
                    content_digest="0" * 64,
                    created_at=utcnow(),
                )
            )
            await db.commit()

            # project RESTRICT：仍有知识库时不能删项目。
            with pytest.raises(DBAPIError) as restricted:
                await db.execute(
                    delete(ProjectContext).where(
                        ProjectContext.project_id == project.project_id
                    )
                )
                await db.commit()
            _assert_constraint_violation(restricted)
            await db.rollback()

            await db.execute(delete(KnowledgeBase).where(KnowledgeBase.kb_id == kb_id))
            await db.commit()
            remaining = await db.scalar(
                select(func.count()).select_from(KnowledgeEntry)
            )
            assert remaining == 0
    finally:
        await database.dispose()


def test_tc144_migration_0007_on_both_dialects(tmp_path) -> None:
    url = _url(tmp_path)
    _upgrade(url)

    up = asyncio.run(_snapshot(url))
    assert up["version"] == "0007"
    assert CORE_TABLES <= up["tables"]
    assert KB_TABLES <= up["tables"]
    assert "knowledge_injection" in up["columns"]["ai_call_record"]

    assert up["uniques"]["knowledge_base"] >= {
        "uq_knowledge_base_project_name_current",
        "uq_knowledge_base_project_name_version",
    }
    assert up["indexes"]["knowledge_base"] >= {
        "ix_knowledge_base_project_current",
        "ix_knowledge_base_project_name",
    }
    assert up["uniques"]["knowledge_entry"] >= {"uq_knowledge_entry_kb_code"}
    assert up["indexes"]["knowledge_entry"] >= {
        "ix_knowledge_entry_code_key",
        "ix_knowledge_entry_kb_type",
    }
    assert up["checks"]["knowledge_base"] >= {
        "ck_knowledge_base_current_flag",
        "ck_knowledge_base_status",
    }
    assert up["checks"]["knowledge_entry"] >= {"ck_knowledge_entry_type"}

    asyncio.run(_cascade_scenario(url))

    command.downgrade(_config(url), "0006")
    down = asyncio.run(_snapshot(url))
    assert down["version"] == "0006"
    assert CORE_TABLES <= down["tables"]
    assert not (KB_TABLES & down["tables"])
    assert "knowledge_injection" in down["columns"]["ai_call_record"]

    command.upgrade(_config(url), "head")
    again = asyncio.run(_snapshot(url))
    assert again["version"] == "0009"
    assert KB_TABLES <= again["tables"]
