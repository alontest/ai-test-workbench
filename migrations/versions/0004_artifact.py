"""会话制品元数据。"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
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
        "artifact",
        sa.Column("artifact_id", _pk(), primary_key=True, autoincrement=True),
        sa.Column("session_id", _pk(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="upload"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column(
            "file_name_key",
            sa.String(length=255).with_variant(
                sa.String(length=255, collation="utf8mb4_bin"), "mysql"
            ),
            nullable=False,
        ),
        sa.Column("storage_name", sa.String(length=120), nullable=False),
        sa.Column("relative_path", sa.String(length=300), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("kind IN ('upload', 'generated')", name="ck_artifact_kind"),
        sa.CheckConstraint("byte_size >= 0", name="ck_artifact_byte_size"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["analysis_session.session_id"],
            name="fk_artifact_session_id_analysis_session",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("artifact_id", name="pk_artifact"),
        sa.UniqueConstraint(
            "session_id", "file_name_key", name="uq_artifact_session_id_file_name_key"
        ),
        sa.UniqueConstraint(
            "session_id", "storage_name", name="uq_artifact_session_id_storage_name"
        ),
        **TABLE_ARGS,
    )
    op.create_index(
        "ix_artifact_session_id_created_at", "artifact", ["session_id", "created_at"]
    )


def downgrade() -> None:
    # 索引随 DROP TABLE 删除；MySQL 不允许先删支撑外键的索引（错误 1553）。
    op.drop_table("artifact")
