"""AI 调用记录（知识库注入四列由 0006 追加）。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def _pk() -> sa.BigInteger:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "ai_call_record",
        sa.Column("call_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("session_id", _pk(), nullable=False),
        sa.Column("model_id", _pk(), nullable=False),
        sa.Column("provider_id", _pk(), nullable=False),
        sa.Column("model_name_snapshot", sa.String(length=191), nullable=False),
        sa.Column("display_name_snapshot", sa.String(length=191), nullable=False),
        sa.Column("provider_name_snapshot", sa.String(length=100), nullable=False),
        sa.Column("protocol_snapshot", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="running"),
        sa.Column("prompt_digest", sa.CHAR(length=64), nullable=False),
        sa.Column("prompt_preview", sa.String(length=200), nullable=False),
        sa.Column("prompt_char_count", sa.Integer(), nullable=False),
        sa.Column(
            "result_text",
            sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"),
            nullable=True,
        ),
        sa.Column("result_format", sa.String(length=16), nullable=False, server_default="text"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed', 'timeout')",
            name="ck_ai_call_record_status",
        ),
        sa.CheckConstraint(
            "retry_count >= 0 AND retry_count <= 1", name="ck_ai_call_record_retry_count"
        ),
        sa.CheckConstraint(
            "prompt_char_count >= 0", name="ck_ai_call_record_prompt_char_count"
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_ai_call_record_session_id_analysis_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["model_id"],
            ["model_binding.model_id"],
            name="fk_ai_call_record_model_id_model_binding",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_config.provider_id"],
            name="fk_ai_call_record_provider_id_provider_config",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("call_id", name="pk_ai_call_record"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_ai_call_record_session_id_call_id", "ai_call_record", ["session_id", "call_id"]
    )
    op.create_index(
        "ix_ai_call_record_status_created_at", "ai_call_record", ["status", "created_at"]
    )
    op.create_index("ix_ai_call_record_created_at", "ai_call_record", ["created_at"])
    op.create_index("ix_ai_call_record_model_id", "ai_call_record", ["model_id"])
    op.create_index("ix_ai_call_record_provider_id", "ai_call_record", ["provider_id"])


def downgrade() -> None:
    op.drop_index("ix_ai_call_record_provider_id", table_name="ai_call_record")
    op.drop_index("ix_ai_call_record_model_id", table_name="ai_call_record")
    op.drop_index("ix_ai_call_record_created_at", table_name="ai_call_record")
    op.drop_index("ix_ai_call_record_status_created_at", table_name="ai_call_record")
    op.drop_index("ix_ai_call_record_session_id_call_id", table_name="ai_call_record")
    op.drop_table("ai_call_record")
