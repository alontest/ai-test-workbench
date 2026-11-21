"""迁移 0008：SQLite 默认，设置 AW_TEST_DATABASE_URL 时在 MySQL 复跑。"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import DBAPIError

from workbench.db.base import Base, utcnow
from workbench.db.engine import Database, create_engine_from_url
from workbench.db.models import (
    ProjectContext,
    RepoBinding,
    RepoFileReadRecord,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)

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
    "knowledge_base",
    "knowledge_entry",
}
REPO_TABLES = {
    "repo_binding",
    "repo_sync_record",
    "repo_metadata_snapshot",
    "repo_file_read_record",
}
CONSTRAINT_MARKERS = (
    "check constraint",
    "unique constraint",
    "duplicate entry",
    "foreign key constraint",
)


def _url(tmp_path) -> str:  # noqa: ANN001
    return os.environ.get(
        "AW_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'repo_migrated.db'}"
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
    command.upgrade(_config(url), "head")


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
        "foreign_keys": {},
    }
    for table in REPO_TABLES & tables:
        result["indexes"][table] = {
            item["name"] for item in inspector.get_indexes(table)
        }
        result["uniques"][table] = {
            item["name"] for item in inspector.get_unique_constraints(table)
        }
        result["checks"][table] = {
            item["name"] for item in inspector.get_check_constraints(table)
        }
        result["foreign_keys"][table] = [
            {
                "columns": item["constrained_columns"],
                "referred_table": item["referred_table"],
                "ondelete": (item.get("options") or {}).get("ondelete"),
            }
            for item in inspector.get_foreign_keys(table)
        ]
    return result


def _assert_constraint_violation(exc_info) -> None:  # noqa: ANN001
    orig = getattr(exc_info.value, "orig", exc_info.value)
    text_ = str(orig).lower()
    assert any(marker in text_ for marker in CONSTRAINT_MARKERS), text_


def _binding(project_id: int, *, repo_key: str, active: bool = True) -> RepoBinding:
    now = utcnow()
    return RepoBinding(
        binding_id=uuid.uuid4().hex,
        project_id=project_id,
        provider="github",
        api_base_url="https://api.github.com",
        owner="pay",
        repo_id="pay/checkout",
        repo_name="pay/checkout",
        repo_key=repo_key,
        display_name="pay/checkout",
        active_flag="1" if active else None,
        created_at=now,
        updated_at=now,
    )


async def _cascade_and_uniqueness(url: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        async with database.sessionmaker() as db:
            name = f"仓库迁移-{uuid.uuid4().hex}"
            project = ProjectContext(name=name, name_key=name)
            db.add(project)
            await db.flush()
            project_id = project.project_id

            binding = _binding(project_id, repo_key="github:pay/checkout")
            db.add(binding)
            await db.flush()
            binding_id = binding.binding_id

            sync_id = uuid.uuid4().hex
            db.add(
                RepoSyncRecord(
                    sync_id=sync_id,
                    binding_id=binding_id,
                    started_at=utcnow(),
                    status="success",
                    repo_count=1,
                    created_at=utcnow(),
                )
            )
            db.add(
                RepoMetadataSnapshot(
                    snapshot_id=uuid.uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    kind="repo",
                    payload={"fullName": "pay/checkout"},
                    fetched_at=utcnow(),
                    truncated=False,
                )
            )
            db.add(
                RepoFileReadRecord(
                    read_id=uuid.uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    ref="main",
                    file_path="src/main.py",
                    byte_size=120,
                    encoding="text",
                    status="success",
                    fetched_at=utcnow(),
                )
            )
            await db.commit()

            # project RESTRICT：仍有绑定时不能删项目。
            with pytest.raises(DBAPIError) as restricted:
                await db.execute(
                    delete(ProjectContext).where(
                        ProjectContext.project_id == project_id
                    )
                )
                await db.commit()
            _assert_constraint_violation(restricted)
            await db.rollback()

            # active_flag 唯一：同项目同 provider 同 repo_key 不能有两条在绑行。
            with pytest.raises(DBAPIError) as duplicate:
                db.add(_binding(project_id, repo_key="github:pay/checkout"))
                await db.commit()
            _assert_constraint_violation(duplicate)
            await db.rollback()

            # 解绑行 active_flag=NULL 不占唯一键，可重新绑定。
            await db.execute(
                text(
                    "UPDATE repo_binding SET active_flag = NULL "
                    "WHERE binding_id = :binding_id"
                ),
                {"binding_id": binding_id},
            )
            await db.commit()
            db.add(_binding(project_id, repo_key="github:pay/checkout"))
            await db.commit()
            active_count = await db.scalar(
                select(func.count())
                .select_from(RepoBinding)
                .where(RepoBinding.active_flag == "1")
            )
            assert active_count == 1

            # 删除绑定 → 三张子表 CASCADE。
            await db.execute(
                delete(RepoBinding).where(RepoBinding.project_id == project_id)
            )
            await db.commit()
            for model in (RepoSyncRecord, RepoMetadataSnapshot, RepoFileReadRecord):
                remaining = await db.scalar(select(func.count()).select_from(model))
                assert remaining == 0
    finally:
        await database.dispose()


def test_tc247_migration_0008_on_both_dialects(tmp_path) -> None:  # noqa: ANN001
    url = _url(tmp_path)
    _upgrade(url)

    assert ScriptDirectory.from_config(_config(url)).get_heads() == ["0008"]

    up = asyncio.run(_snapshot(url))
    assert up["version"] == "0008"
    assert CORE_TABLES <= up["tables"]
    assert REPO_TABLES <= up["tables"]

    assert up["indexes"]["repo_binding"] >= {
        "ix_repo_binding_project_status",
        "ix_repo_binding_project_created",
    }
    assert up["indexes"]["repo_sync_record"] >= {
        "ix_repo_sync_record_binding_started"
    }
    assert up["indexes"]["repo_metadata_snapshot"] >= {
        "ix_repo_metadata_snapshot_binding_kind_fetched",
        "ix_repo_metadata_snapshot_binding_fetched",
    }
    assert up["indexes"]["repo_file_read_record"] >= {
        "ix_repo_file_read_record_binding_fetched"
    }
    assert up["uniques"]["repo_binding"] >= {
        "uq_repo_binding_project_provider_repo_active"
    }
    assert up["checks"]["repo_binding"] >= {
        "ck_repo_binding_provider",
        "ck_repo_binding_status",
        "ck_repo_binding_active_flag",
        "ck_repo_binding_last_verify_result",
        "ck_repo_binding_last_sync_status",
        "ck_repo_binding_last_sync_error_category",
    }
    assert up["checks"]["repo_sync_record"] >= {
        "ck_repo_sync_record_status",
        "ck_repo_sync_record_error_category",
    }
    assert up["checks"]["repo_metadata_snapshot"] >= {
        "ck_repo_metadata_snapshot_kind"
    }
    assert up["checks"]["repo_file_read_record"] >= {
        "ck_repo_file_read_record_encoding",
        "ck_repo_file_read_record_status",
        "ck_repo_file_read_record_reject_reason",
    }

    binding_fk = up["foreign_keys"]["repo_binding"]
    assert binding_fk == [
        {
            "columns": ["project_id"],
            "referred_table": "project_context",
            "ondelete": "RESTRICT",
        }
    ]
    for table in (
        "repo_sync_record",
        "repo_metadata_snapshot",
        "repo_file_read_record",
    ):
        fks = up["foreign_keys"][table]
        assert len(fks) == 1
        assert fks[0]["columns"] == ["binding_id"]
        assert fks[0]["referred_table"] == "repo_binding"
        assert (fks[0]["ondelete"] or "").upper() == "CASCADE"

    asyncio.run(_cascade_and_uniqueness(url))

    command.downgrade(_config(url), "0007")
    down = asyncio.run(_snapshot(url))
    assert down["version"] == "0007"
    assert CORE_TABLES <= down["tables"]
    assert not (REPO_TABLES & down["tables"])

    command.upgrade(_config(url), "head")
    again = asyncio.run(_snapshot(url))
    assert again["version"] == "0008"
    assert REPO_TABLES <= again["tables"]
