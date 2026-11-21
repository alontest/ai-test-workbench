"""知识库两张新表：knowledge_base / knowledge_entry。

只新增本 spec 的表；不修改 core 的 10 张表，不建指向 ai_call_record /
session_event 的外键。升级顺序父表在前，降级反序。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0007"
down_revision = "0006"
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
        "knowledge_base",
        sa.Column("kb_id", sa.CHAR(length=32), nullable=False),
        sa.Column("project_id", _pk(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("name_key", sa.String(length=200), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("current_flag", sa.CHAR(length=1), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="ready"
        ),
        sa.Column("index_generated_at", sa.DateTime(), nullable=True),
        sa.Column("entry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "total_byte_size", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("source_index_sha256", sa.CHAR(length=64), nullable=False),
        sa.Column("storage_dir", sa.String(length=191), nullable=False),
        sa.Column("superseded_by_kb_id", sa.CHAR(length=32), nullable=True),
        sa.Column("import_report", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "current_flag IS NULL OR current_flag = '1'",
            name="ck_knowledge_base_current_flag",
        ),
        sa.CheckConstraint(
            "status IN ('ready', 'superseded')", name="ck_knowledge_base_status"
        ),
        sa.CheckConstraint("version >= 1", name="ck_knowledge_base_version"),
        sa.CheckConstraint(
            "entry_count >= 0", name="ck_knowledge_base_entry_count"
        ),
        sa.CheckConstraint("file_count >= 0", name="ck_knowledge_base_file_count"),
        sa.CheckConstraint(
            "total_byte_size >= 0", name="ck_knowledge_base_total_byte_size"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_knowledge_base_project_id_project_context",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("kb_id", name="pk_knowledge_base"),
        sa.UniqueConstraint(
            "project_id",
            "name_key",
            "current_flag",
            name="uq_knowledge_base_project_name_current",
        ),
        sa.UniqueConstraint(
            "project_id",
            "name_key",
            "version",
            name="uq_knowledge_base_project_name_version",
        ),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_knowledge_base_project_current",
        "knowledge_base",
        ["project_id", "current_flag"],
    )
    op.create_index(
        "ix_knowledge_base_project_name",
        "knowledge_base",
        ["project_id", "name_key"],
    )

    op.create_table(
        "knowledge_entry",
        sa.Column("entry_id", sa.CHAR(length=32), nullable=False),
        sa.Column("kb_id", sa.CHAR(length=32), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("code_key", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", _medium_text(), nullable=False, server_default=""),
        sa.Column("body", _medium_text(), nullable=True),
        sa.Column(
            "body_missing", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("body_source_file", sa.String(length=255), nullable=True),
        sa.Column("fields", sa.JSON(), nullable=True),
        sa.Column("tables", sa.JSON(), nullable=True),
        sa.Column("code_paths", sa.JSON(), nullable=True),
        sa.Column("neighbors", sa.JSON(), nullable=True),
        sa.Column("extras", sa.JSON(), nullable=True),
        sa.Column("source_doc", sa.String(length=100), nullable=True),
        sa.Column("anchor", sa.String(length=200), nullable=True),
        sa.Column("freshness_at", sa.DateTime(), nullable=True),
        sa.Column("content_digest", sa.CHAR(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "type IN ('term', 'entity', 'state', 'rule', 'process', 'api', "
            "'domain_event', 'other')",
            name="ck_knowledge_entry_type",
        ),
        sa.ForeignKeyConstraint(
            ["kb_id"],
            ["knowledge_base.kb_id"],
            name="fk_knowledge_entry_kb_id_knowledge_base",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("entry_id", name="pk_knowledge_entry"),
        sa.UniqueConstraint("kb_id", "code_key", name="uq_knowledge_entry_kb_code"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_knowledge_entry_code_key", "knowledge_entry", ["code_key"]
    )
    op.create_index(
        "ix_knowledge_entry_kb_type", "knowledge_entry", ["kb_id", "type"]
    )


def downgrade() -> None:
    op.drop_table("knowledge_entry")
    op.drop_table("knowledge_base")
