"""认证侧三张表：admin_credential / login_session / login_attempt。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "admin_credential",
        # 固定单行（credential_id = 1），显式关闭自增：
        # MySQL 8 不允许 CHECK 引用 AUTO_INCREMENT 列（错误 3818）。
        sa.Column(
            "credential_id", sa.SmallInteger(), primary_key=True, autoincrement=False
        ),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("credential_id = 1", name="ck_admin_credential_credential_id"),
        sa.PrimaryKeyConstraint("credential_id", name="pk_admin_credential"),
        **TABLE_ARGS,
    )
    op.create_table(
        "login_session",
        sa.Column(
            "login_session_id",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("source_ip_hash", sa.CHAR(length=64), nullable=True),
        sa.PrimaryKeyConstraint("login_session_id", name="pk_login_session"),
        sa.UniqueConstraint("token_hash", name="uq_login_session_token_hash"),
        **TABLE_ARGS,
    )
    op.create_index("ix_login_session_last_seen_at", "login_session", ["last_seen_at"])
    op.create_index("ix_login_session_revoked_at", "login_session", ["revoked_at"])
    op.create_table(
        "login_attempt",
        sa.Column("source_ip_hash", sa.CHAR(length=64), primary_key=True),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_failed_at", sa.DateTime(), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(), nullable=False),
        sa.Column("locked_until", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("source_ip_hash", name="pk_login_attempt"),
        **TABLE_ARGS,
    )
    op.create_index("ix_login_attempt_last_failed_at", "login_attempt", ["last_failed_at"])


def downgrade() -> None:
    op.drop_index("ix_login_attempt_last_failed_at", table_name="login_attempt")
    op.drop_table("login_attempt")
    op.drop_index("ix_login_session_revoked_at", table_name="login_session")
    op.drop_index("ix_login_session_last_seen_at", table_name="login_session")
    op.drop_table("login_session")
    op.drop_table("admin_credential")
