"""测试设计最小闭环五张新表：qa_skill / qa_skill_version /
approval_request / test_case_design_plan / test_case。

只新增本 spec 的表；不修改既有表。升级顺序父表在前，降级反序。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _pk() -> sa.BigInteger:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _medium_text() -> sa.Text:
    return sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def upgrade() -> None:
    op.create_table(
        "qa_skill",
        sa.Column("skill_id", sa.CHAR(length=32), nullable=False),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("scope_key", sa.String(length=64), nullable=False),
        sa.Column("project_id", _pk(), nullable=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "domain",
            sa.String(length=32),
            nullable=False,
            server_default="test-case",
        ),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("triggers", sa.JSON(), nullable=False),
        sa.Column("content_md", _medium_text(), nullable=False),
        sa.Column(
            "current_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "is_builtin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "scope IN ('global', 'project')",
            name="ck_qa_skill_scope",
        ),
        sa.CheckConstraint(
            "(scope = 'global' AND project_id IS NULL) OR "
            "(scope = 'project' AND project_id IS NOT NULL)",
            name="ck_qa_skill_scope_project",
        ),
        sa.CheckConstraint(
            "domain IN ('test-case', 'diagnosis', 'regression-list', "
            "'test-report', 'general')",
            name="ck_qa_skill_domain",
        ),
        sa.CheckConstraint(
            "current_version >= 1",
            name="ck_qa_skill_version",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_qa_skill_project_id_project_context",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("skill_id", name="pk_qa_skill"),
        sa.UniqueConstraint(
            "scope_key", "slug", name="uq_qa_skill_scope_slug"
        ),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_qa_skill_project_domain",
        "qa_skill",
        ["project_id", "domain"],
    )

    op.create_table(
        "qa_skill_version",
        sa.Column("version_id", sa.CHAR(length=32), nullable=False),
        sa.Column("skill_id", sa.CHAR(length=32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_md", _medium_text(), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("approval_id", sa.CHAR(length=32), nullable=True),
        sa.Column("session_id", _pk(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_qa_skill_version_num",
        ),
        sa.CheckConstraint(
            "source_type IN ('builtin', 'human', 'agent_proposal', 'rollback')",
            name="ck_qa_skill_version_source",
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["qa_skill.skill_id"],
            name="fk_qa_skill_version_skill_id_qa_skill",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("version_id", name="pk_qa_skill_version"),
        sa.UniqueConstraint(
            "skill_id", "version", name="uq_qa_skill_version_skill_ver"
        ),
        **TABLE_ARGS,
    )

    op.create_table(
        "approval_request",
        sa.Column("approval_id", sa.CHAR(length=32), nullable=False),
        sa.Column("project_id", _pk(), nullable=True),
        sa.Column("session_id", _pk(), nullable=True),
        sa.Column("call_id", _pk(), nullable=True),
        sa.Column(
            "target_type",
            sa.String(length=32),
            nullable=False,
            server_default="qa_skill",
        ),
        sa.Column("target_id", sa.CHAR(length=32), nullable=False),
        sa.Column("target_title", sa.String(length=200), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("before_content", _medium_text(), nullable=False),
        sa.Column("after_content", _medium_text(), nullable=False),
        sa.Column("unified_diff", _medium_text(), nullable=False),
        sa.Column("rationale", sa.String(length=1000), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("decision_note", sa.String(length=500), nullable=True),
        sa.Column("applied_version", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "target_type IN ('qa_skill')",
            name="ck_approval_request_target_type",
        ),
        sa.CheckConstraint(
            "action_type IN ('update_skill', 'create_skill')",
            name="ck_approval_request_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_approval_request_status",
        ),
        sa.CheckConstraint(
            "base_version >= 0",
            name="ck_approval_request_base_version",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_approval_request_project_id_project_context",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_approval_request_session_id_analysis_session",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("approval_id", name="pk_approval_request"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_approval_request_status_created",
        "approval_request",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_approval_request_project_created",
        "approval_request",
        ["project_id", "created_at"],
    )

    op.create_table(
        "test_case_design_plan",
        sa.Column("plan_id", sa.CHAR(length=32), nullable=False),
        sa.Column("project_id", _pk(), nullable=False),
        sa.Column("session_id", _pk(), nullable=False),
        sa.Column("call_id", _pk(), nullable=True),
        sa.Column("skill_id", sa.CHAR(length=32), nullable=True),
        sa.Column("skill_version", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("requirement_text", _medium_text(), nullable=False),
        sa.Column("checkpoints", sa.JSON(), nullable=False),
        sa.Column("kb_links", sa.JSON(), nullable=False),
        sa.Column("code_paths", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'generated')",
            name="ck_test_case_design_plan_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_test_case_design_plan_project_id_project_context",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_test_case_design_plan_session_id_analysis_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("plan_id", name="pk_test_case_design_plan"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_test_case_design_plan_project_created",
        "test_case_design_plan",
        ["project_id", "created_at"],
    )

    op.create_table(
        "test_case",
        sa.Column("case_id", sa.CHAR(length=32), nullable=False),
        sa.Column("project_id", _pk(), nullable=False),
        sa.Column("plan_id", sa.CHAR(length=32), nullable=True),
        sa.Column("checkpoint_id", sa.String(length=64), nullable=True),
        sa.Column("session_id", _pk(), nullable=True),
        sa.Column("call_id", _pk(), nullable=True),
        sa.Column("skill_id", sa.CHAR(length=32), nullable=True),
        sa.Column("skill_version", sa.Integer(), nullable=True),
        sa.Column("case_code", sa.String(length=64), nullable=False),
        sa.Column("module", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=16),
            nullable=False,
            server_default="P1",
        ),
        sa.Column(
            "case_type",
            sa.String(length=32),
            nullable=False,
            server_default="functional",
        ),
        sa.Column("preconditions", sa.JSON(), nullable=False),
        sa.Column("steps", sa.JSON(), nullable=False),
        sa.Column("expected_summary", _medium_text(), nullable=False),
        sa.Column("kb_links", sa.JSON(), nullable=False),
        sa.Column("code_paths", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "priority IN ('P0', 'P1', 'P2', 'P3')",
            name="ck_test_case_priority",
        ),
        sa.CheckConstraint(
            "case_type IN ('functional', 'boundary', 'exception', "
            "'security', 'concurrency')",
            name="ck_test_case_type",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_test_case_project_id_project_context",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["test_case_design_plan.plan_id"],
            name="fk_test_case_plan_id_test_case_design_plan",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_test_case_session_id_analysis_session",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("case_id", name="pk_test_case"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_test_case_project_module",
        "test_case",
        ["project_id", "module"],
    )
    op.create_index(
        "ix_test_case_project_updated",
        "test_case",
        ["project_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_table("test_case")
    op.drop_table("test_case_design_plan")
    op.drop_table("approval_request")
    op.drop_table("qa_skill_version")
    op.drop_table("qa_skill")
