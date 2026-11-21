from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, utcnow


class RepoMetadataSnapshot(Base):
    """一行 = 一条基线元数据；每次成功同步全量替换，不含文件正文。"""

    __tablename__ = "repo_metadata_snapshot"

    snapshot_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    binding_id = Column(
        CHAR(32),
        ForeignKey("repo_binding.binding_id", ondelete="CASCADE"),
        nullable=False,
    )
    repo_id = Column(String(191), nullable=False)
    kind = Column(String(20), nullable=False)
    ref = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)
    truncated = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            "kind IN ('repo', 'branch', 'commit', 'tree')",
            name="ck_repo_metadata_snapshot_kind",
        ),
        Index(
            "ix_repo_metadata_snapshot_binding_kind_fetched",
            "binding_id",
            "kind",
            "fetched_at",
        ),
        Index(
            "ix_repo_metadata_snapshot_binding_fetched",
            "binding_id",
            "fetched_at",
        ),
        MYSQL_TABLE_ARGS,
    )
