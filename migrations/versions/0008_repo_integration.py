"""仓库集成四张新表：repo_binding / repo_sync_record /
repo_metadata_snapshot / repo_file_read_record。

只新增本 spec 的表；不修改 core 与 knowledge-base 的既有表。升级顺序父表在
前，降级反序。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
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
        "repo_binding",
        sa.Column("binding_id", sa.CHAR(length=32), nullable=False),
        sa.Column("project_id", _pk(), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("api_base_url", sa.String(length=255), nullable=False),
        sa.Column("org_id", sa.String(length=128), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("repo_id", sa.String(length=191), nullable=True),
        sa.Column("repo_name", sa.String(length=255), nullable=False),
        sa.Column("repo_key", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("default_branch", sa.String(length=255), nullable=True),
        sa.Column("token_ciphertext", sa.String(length=2048), nullable=True),
        sa.Column("token_masked", sa.String(length=64), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="unverified",
        ),
        sa.Column(
            "active_flag",
            sa.CHAR(length=1),
            nullable=True,
            server_default=sa.text("'1'"),
        ),
        sa.Column("last_verified_at", sa.DateTime(), nullable=True),
        sa.Column("last_verify_result", sa.String(length=20), nullable=True),
        sa.Column("last_verify_message", sa.String(length=500), nullable=True),
        sa.Column("last_sync_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_status", sa.String(length=20), nullable=True),
        sa.Column("last_sync_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_sync_duration_ms", sa.Integer(), nullable=True),
        sa.Column("last_sync_error_category", sa.String(length=20), nullable=True),
        sa.Column("last_sync_error_message", sa.String(length=500), nullable=True),
        sa.Column("last_sync_retry_after", sa.DateTime(), nullable=True),
        sa.Column("sync_started_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "provider IN ('yunxiao', 'github')",
            name="ck_repo_binding_provider",
        ),
        sa.CheckConstraint(
            "status IN ('unverified', 'connected', 'token_invalid', 'revoked')",
            name="ck_repo_binding_status",
        ),
        sa.CheckConstraint(
            "active_flag IS NULL OR active_flag = '1'",
            name="ck_repo_binding_active_flag",
        ),
        sa.CheckConstraint(
            "last_verify_result IS NULL OR last_verify_result IN "
            "('success', 'auth-error', 'unreachable', 'permission-denied')",
            name="ck_repo_binding_last_verify_result",
        ),
        sa.CheckConstraint(
            "last_sync_status IS NULL OR last_sync_status IN "
            "('success', 'failed')",
            name="ck_repo_binding_last_sync_status",
        ),
        sa.CheckConstraint(
            "last_sync_error_category IS NULL OR last_sync_error_category IN "
            "('auth', 'network', 'rate_limit', 'permission', 'other', "
            "'interrupted')",
            name="ck_repo_binding_last_sync_error_category",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project_context.project_id"],
            name="fk_repo_binding_project_id_project_context",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("binding_id", name="pk_repo_binding"),
        sa.UniqueConstraint(
            "project_id",
            "provider",
            "repo_key",
            "active_flag",
            name="uq_repo_binding_project_provider_repo_active",
        ),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_repo_binding_project_status",
        "repo_binding",
        ["project_id", "status"],
    )
    op.create_index(
        "ix_repo_binding_project_created",
        "repo_binding",
        ["project_id", "created_at"],
    )

    op.create_table(
        "repo_sync_record",
        sa.Column("sync_id", sa.CHAR(length=32), nullable=False),
        sa.Column("binding_id", sa.CHAR(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="running",
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("repo_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("branch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_category", sa.String(length=20), nullable=True),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("retry_after_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_repo_sync_record_status",
        ),
        sa.CheckConstraint(
            "error_category IS NULL OR error_category IN "
            "('auth', 'network', 'rate_limit', 'permission', 'other', "
            "'interrupted')",
            name="ck_repo_sync_record_error_category",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["repo_binding.binding_id"],
            name="fk_repo_sync_record_binding_id_repo_binding",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("sync_id", name="pk_repo_sync_record"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_repo_sync_record_binding_started",
        "repo_sync_record",
        ["binding_id", "started_at"],
    )

    op.create_table(
        "repo_metadata_snapshot",
        sa.Column("snapshot_id", sa.CHAR(length=32), nullable=False),
        sa.Column("binding_id", sa.CHAR(length=32), nullable=False),
        sa.Column("repo_id", sa.String(length=191), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("ref", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.Column(
            "truncated", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.CheckConstraint(
            "kind IN ('repo', 'branch', 'commit', 'tree')",
            name="ck_repo_metadata_snapshot_kind",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["repo_binding.binding_id"],
            name="fk_repo_metadata_snapshot_binding_id_repo_binding",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("snapshot_id", name="pk_repo_metadata_snapshot"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_repo_metadata_snapshot_binding_kind_fetched",
        "repo_metadata_snapshot",
        ["binding_id", "kind", "fetched_at"],
    )
    op.create_index(
        "ix_repo_metadata_snapshot_binding_fetched",
        "repo_metadata_snapshot",
        ["binding_id", "fetched_at"],
    )

    op.create_table(
        "repo_file_read_record",
        sa.Column("read_id", sa.CHAR(length=32), nullable=False),
        sa.Column("binding_id", sa.CHAR(length=32), nullable=False),
        sa.Column("repo_id", sa.String(length=191), nullable=False),
        sa.Column("ref", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("encoding", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("reject_reason", sa.String(length=20), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "encoding IN ('text', 'base64')",
            name="ck_repo_file_read_record_encoding",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'refused')",
            name="ck_repo_file_read_record_status",
        ),
        sa.CheckConstraint(
            "reject_reason IS NULL OR reject_reason IN "
            "('too_large', 'binary', 'not_utf8')",
            name="ck_repo_file_read_record_reject_reason",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id"],
            ["repo_binding.binding_id"],
            name="fk_repo_file_read_record_binding_id_repo_binding",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("read_id", name="pk_repo_file_read_record"),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_repo_file_read_record_binding_fetched",
        "repo_file_read_record",
        ["binding_id", "fetched_at"],
    )


def downgrade() -> None:
    op.drop_table("repo_file_read_record")
    op.drop_table("repo_metadata_snapshot")
    op.drop_table("repo_sync_record")
    op.drop_table("repo_binding")
