"""项目 / 提供商 / 模型三张表。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision = "0002"
down_revision = "0001"
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
        "project_context",
        sa.Column("project_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "name_key",
            sa.String(length=100).with_variant(
                sa.String(length=100, collation="utf8mb4_bin"), "mysql"
            ),
            nullable=False,
        ),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("tech_stack", sa.String(length=500), nullable=True),
        sa.Column(
            "requirement_source",
            sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "notes", sa.Text().with_variant(mysql.MEDIUMTEXT(), "mysql"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("project_id", name="pk_project_context"),
        sa.UniqueConstraint("name_key", name="uq_project_context_name_key"),
        **TABLE_ARGS,
    )
    op.create_index("ix_project_context_updated_at", "project_context", ["updated_at"])
    op.create_table(
        "provider_config",
        sa.Column("provider_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("protocol", sa.String(length=32), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key_ciphertext", sa.String(length=1024), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "protocol IN ('openai_compatible', 'anthropic')",
            name="ck_provider_config_protocol",
        ),
        sa.PrimaryKeyConstraint("provider_id", name="pk_provider_config"),
        **TABLE_ARGS,
    )
    op.create_index("ix_provider_config_enabled", "provider_config", ["enabled"])
    op.create_table(
        "model_binding",
        sa.Column("model_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("provider_id", _pk(), nullable=False),
        sa.Column("model_name", sa.String(length=191), nullable=False),
        sa.Column(
            "model_name_key",
            sa.String(length=191).with_variant(
                sa.String(length=191, collation="utf8mb4_bin"), "mysql"
            ),
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=191), nullable=False),
        sa.Column("default_temperature", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "default_max_tokens", sa.Integer(), nullable=False, server_default="4096"
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "default_temperature >= 0 AND default_temperature <= 2",
            name="ck_model_binding_default_temperature",
        ),
        sa.CheckConstraint(
            "default_max_tokens > 0 AND default_max_tokens <= 1000000",
            name="ck_model_binding_default_max_tokens",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["provider_config.provider_id"],
            name="fk_model_binding_provider_id_provider_config",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("model_id", name="pk_model_binding"),
        sa.UniqueConstraint(
            "provider_id",
            "model_name_key",
            name="uq_model_binding_provider_id_model_name_key",
        ),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_model_binding_provider_id_enabled", "model_binding", ["provider_id", "enabled"]
    )


def downgrade() -> None:
    # 索引随 DROP TABLE 删除；MySQL 不允许先删支撑外键的索引（错误 1553）。
    op.drop_table("model_binding")
    op.drop_table("provider_config")
    op.drop_table("project_context")
