"""迁移 0009：测试设计最小闭环五张表（qa_skill / qa_skill_version /
approval_request / test_case_design_plan / test_case）及双方言约束。"""

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
    ApprovalRequest,
    ProjectContext,
    QaSkill,
    QaSkillVersion,
    TestCase,
)

PREV_TABLES = {
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
}
TC_LOOP_TABLES = {
    "qa_skill",
    "qa_skill_version",
    "approval_request",
    "test_case_design_plan",
    "test_case",
}
CONSTRAINT_MARKERS = (
    "check constraint",
    "unique constraint",
    "duplicate entry",
    "foreign key constraint",
)


def _url(tmp_path) -> str:  # noqa: ANN001
    return os.environ.get(
        "AW_TEST_DATABASE_URL",
        f"sqlite+aiosqlite:///{tmp_path / 'tc_loop_migrated.db'}",
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
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar()
        ),
        "indexes": {},
        "uniques": {},
        "checks": {},
    }
    for table in TC_LOOP_TABLES & tables:
        result["indexes"][table] = {
            item["name"] for item in inspector.get_indexes(table)
        }
        result["uniques"][table] = {
            item["name"] for item in inspector.get_unique_constraints(table)
        }
        result["checks"][table] = {
            item["name"] for item in inspector.get_check_constraints(table)
        }
    return result


def _assert_constraint_violation(exc_info) -> None:  # noqa: ANN001
    orig = getattr(exc_info.value, "orig", exc_info.value)
    text_ = str(orig).lower()
    assert any(marker in text_ for marker in CONSTRAINT_MARKERS), text_


def test_tc301_migration_0009_schema_and_downgrade(tmp_path) -> None:  # noqa: ANN001
    url = _url(tmp_path)
    _upgrade(url)

    assert ScriptDirectory.from_config(_config(url)).get_heads() == ["0009"]

    up = asyncio.run(_snapshot(url))
    assert up["version"] == "0009"
    assert PREV_TABLES <= up["tables"]
    assert TC_LOOP_TABLES <= up["tables"]

    assert up["uniques"]["qa_skill"] >= {"uq_qa_skill_scope_slug"}
    assert up["indexes"]["qa_skill"] >= {"ix_qa_skill_project_domain"}
    assert up["checks"]["qa_skill"] >= {
        "ck_qa_skill_scope",
        "ck_qa_skill_scope_project",
        "ck_qa_skill_domain",
        "ck_qa_skill_version",
    }

    assert up["uniques"]["qa_skill_version"] >= {"uq_qa_skill_version_skill_ver"}
    assert up["checks"]["qa_skill_version"] >= {
        "ck_qa_skill_version_num",
        "ck_qa_skill_version_source",
    }

    assert up["indexes"]["approval_request"] >= {
        "ix_approval_request_status_created",
        "ix_approval_request_project_created",
    }
    assert up["checks"]["approval_request"] >= {
        "ck_approval_request_target_type",
        "ck_approval_request_action_type",
        "ck_approval_request_status",
        "ck_approval_request_base_version",
    }

    assert up["indexes"]["test_case_design_plan"] >= {
        "ix_test_case_design_plan_project_created"
    }
    assert up["checks"]["test_case_design_plan"] >= {
        "ck_test_case_design_plan_status"
    }

    assert up["indexes"]["test_case"] >= {
        "ix_test_case_project_module",
        "ix_test_case_project_updated",
    }
    assert up["checks"]["test_case"] >= {
        "ck_test_case_priority",
        "ck_test_case_type",
    }

    command.downgrade(_config(url), "0008")
    down = asyncio.run(_snapshot(url))
    assert down["version"] == "0008"
    assert PREV_TABLES <= down["tables"]
    assert not (TC_LOOP_TABLES & down["tables"])

    command.upgrade(_config(url), "head")
    again = asyncio.run(_snapshot(url))
    assert again["version"] == "0009"
    assert TC_LOOP_TABLES <= again["tables"]


async def _constraints_scenario(url: str) -> None:
    database = Database(create_engine_from_url(url))
    try:
        async with database.sessionmaker() as db:
            name = f"测试设计迁移-{uuid.uuid4().hex}"
            project = ProjectContext(name=name, name_key=name)
            db.add(project)
            await db.flush()
            project_id = project.project_id

            now = utcnow()
            skill_id = uuid.uuid4().hex
            db.add(
                QaSkill(
                    skill_id=skill_id,
                    scope="global",
                    scope_key="global",
                    project_id=None,
                    slug="two-stage-test-case-design",
                    name="两阶段测试设计规范",
                    domain="test-case",
                    description="内置规范",
                    triggers=["case-library"],
                    content_md="# 规范 v1",
                    current_version=1,
                    is_builtin=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                QaSkillVersion(
                    version_id=uuid.uuid4().hex,
                    skill_id=skill_id,
                    version=1,
                    content_md="# 规范 v1",
                    change_summary="初始内置版本",
                    source_type="builtin",
                    created_at=now,
                )
            )
            await db.commit()

            # 1) 全局技能同名 slug 必须冲突（scope_key='global' 消除 NULL != NULL 盲区）
            with pytest.raises(DBAPIError) as dup_global:
                db.add(
                    QaSkill(
                        skill_id=uuid.uuid4().hex,
                        scope="global",
                        scope_key="global",
                        project_id=None,
                        slug="two-stage-test-case-design",
                        name="重复全局技能",
                        domain="test-case",
                        description="重复",
                        triggers=[],
                        content_md="# dup",
                        current_version=1,
                        is_builtin=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()
            _assert_constraint_violation(dup_global)
            await db.rollback()

            # 2) scope 与 project_id 不匹配时触发 ck_qa_skill_scope_project
            with pytest.raises(DBAPIError) as bad_scope:
                db.add(
                    QaSkill(
                        skill_id=uuid.uuid4().hex,
                        scope="global",
                        scope_key="global",
                        project_id=project_id,
                        slug="bad-global-with-project",
                        name="非法作用域",
                        domain="test-case",
                        description="非法",
                        triggers=[],
                        content_md="# bad",
                        current_version=1,
                        is_builtin=False,
                        created_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()
            _assert_constraint_violation(bad_scope)
            await db.rollback()

            # 3) 项目级同名 slug 允许与全局并存，但同项目内不可重复
            proj_skill_id = uuid.uuid4().hex
            db.add(
                QaSkill(
                    skill_id=proj_skill_id,
                    scope="project",
                    scope_key=f"project:{project_id}",
                    project_id=project_id,
                    slug="two-stage-test-case-design",
                    name="项目定制规范",
                    domain="test-case",
                    description="项目级",
                    triggers=["case-library"],
                    content_md="# 项目规范",
                    current_version=1,
                    is_builtin=False,
                    created_at=now,
                    updated_at=now,
                )
            )
            await db.commit()

            # 4) approval_request 与 test_case CHECK 约束生效
            with pytest.raises(DBAPIError) as bad_approval:
                db.add(
                    ApprovalRequest(
                        approval_id=uuid.uuid4().hex,
                        project_id=project_id,
                        target_type="qa_skill",
                        target_id=skill_id,
                        target_title="规范",
                        action_type="update_skill",
                        base_version=1,
                        before_content="a",
                        after_content="b",
                        unified_diff="@@",
                        rationale="r",
                        status="invalid_status",
                        created_at=now,
                    )
                )
                await db.commit()
            _assert_constraint_violation(bad_approval)
            await db.rollback()

            with pytest.raises(DBAPIError) as bad_priority:
                db.add(
                    TestCase(
                        case_id=uuid.uuid4().hex,
                        project_id=project_id,
                        case_code="TC-ORD-001",
                        module="订单",
                        title="超时关闭",
                        priority="P9",
                        case_type="functional",
                        preconditions=[],
                        steps=[],
                        expected_summary="关闭成功",
                        kb_links=[],
                        code_paths=[],
                        created_at=now,
                        updated_at=now,
                    )
                )
                await db.commit()
            _assert_constraint_violation(bad_priority)
            await db.rollback()

            # 5) 删除 qa_skill 级联清理 qa_skill_version
            await db.execute(
                delete(QaSkill).where(QaSkill.skill_id == skill_id)
            )
            await db.commit()
            ver_count = await db.scalar(
                select(func.count())
                .select_from(QaSkillVersion)
                .where(QaSkillVersion.skill_id == skill_id)
            )
            assert ver_count == 0
    finally:
        await database.dispose()


def test_tc302_migration_0009_constraints_and_cascades(tmp_path) -> None:  # noqa: ANN001
    url = _url(tmp_path)
    _upgrade(url)
    asyncio.run(_constraints_scenario(url))
