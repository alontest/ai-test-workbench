"""会话与时间线事件。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}

ENTRANCE_CHECK = (
    "entrance_key IN ('case-library', 'bug-analysis', 'log-triage', "
    "'sql-analysis', 'regression-list', 'test-report')"
)


def _pk() -> sa.BigInteger:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "analysis_session",
        sa.Column("session_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("project_id", _pk(), nullable=False),
        sa.Column("entrance_key", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="in_progress"
        ),
        sa.Column("model_id", _pk(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(ENTRANCE_CHECK, name="ck_analysis_session_entrance_key"),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed')",
            name="ck_analysis_session_status",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_analysis_session_project_id_project_context",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["model_binding.model_id"],
            name="fk_analysis_session_model_id_model_binding",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("session_id", name="pk_analysis_session"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_analysis_session_project_id_updated_at",
        "analysis_session",
        ["project_id", "updated_at"],
    )
    op.create_index(
        "ix_analysis_session_status_updated_at",
        "analysis_session",
        ["status", "updated_at"],
    )
    op.create_index("ix_analysis_session_updated_at", "analysis_session", ["updated_at"])
    op.create_index("ix_analysis_session_model_id", "analysis_session", ["model_id"])
    op.create_table(
        "session_event",
        sa.Column("event_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("session_id", _pk(), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "type IN ('input_text', 'artifact', 'call', 'status_change')",
            name="ck_session_event_type",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_session_event_session_id_analysis_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_session_event"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_session_event_session_id_event_id",
        "session_event",
        ["session_id", "event_id"],
    )


def downgrade() -> None:
    # 索引随 DROP TABLE 删除；MySQL 不允许先删支撑外键的索引（错误 1553）。
    op.drop_table("session_event")
    op.drop_table("analysis_session")
