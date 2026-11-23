"""引擎与模型元数据。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, StaticPool

from vigil_workbench.db.base import Base
from vigil_workbench.db.engine import create_engine_from_url


@pytest.mark.asyncio
async def test_tc058_engine_creation_both_dialects(tmp_path) -> None:
    db_engine = create_engine_from_url(f"sqlite+aiosqlite:///{tmp_path / 'x.db'}")
    assert isinstance(db_engine.pool, NullPool)
    mem_engine = create_engine_from_url("sqlite+aiosqlite:///:memory:")
    assert isinstance(mem_engine.pool, StaticPool)

    mysql_engine = create_engine_from_url(
        "mysql+asyncmy://user:password@127.0.0.1:3306/vigil?charset=utf8mb4"
    )
    assert mysql_engine.dialect.name == "mysql"
    assert isinstance(mysql_engine.pool, AsyncAdaptedQueuePool)
    assert mysql_engine.pool.size() == 5
    assert mysql_engine.pool._max_overflow == 5

    await db_engine.dispose()
    await mem_engine.dispose()
    await mysql_engine.dispose()


def test_tc058_models_match_schema_metadata() -> None:
    tables = Base.metadata.tables
    assert set(tables) == {
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
        "repo_binding",
        "repo_sync_record",
        "repo_metadata_snapshot",
        "repo_file_read_record",
        "qa_skill",
        "qa_skill_version",
        "approval_request",
        "test_case_design_plan",
        "test_case",
    }
    assert {
        "knowledge_injection",
        "injected_chars",
        "prompt_chars",
        "total_chars",
    } <= set(tables["ai_call_record"].columns.keys())
    checks = " ".join(str(c.sqltext) for c in tables["session_event"].constraints if hasattr(c, "sqltext"))
    assert "knowledge_injection" in checks
    unique_names = {c.name for c in tables["artifact"].constraints}
    assert "uq_artifact_session_id_file_name_key" in unique_names
    assert "uq_artifact_session_id_storage_name" in unique_names
    fk_targets = {
        (fk.parent.name, fk.target_fullname, fk.ondelete)
        for fk in tables["analysis_session"].foreign_keys
    }
    assert ("project_id", "project_context.project_id", "RESTRICT") in fk_targets
    assert ("model_id", "model_binding.model_id", "RESTRICT") in fk_targets
