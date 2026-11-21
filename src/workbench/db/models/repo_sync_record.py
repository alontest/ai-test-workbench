from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, utcnow


class RepoSyncRecord(Base):
    """一行 = 一次手动同步尝试（成功与失败都写）。"""

    __tablename__ = "repo_sync_record"

    sync_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    binding_id = Column(
        CHAR(32),
        ForeignKey("repo_binding.binding_id", ondelete="CASCADE"),
        nullable=False,
    )
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="running")
    duration_ms = Column(Integer, nullable=True)
    repo_count = Column(Integer, nullable=False, default=0)
    branch_count = Column(Integer, nullable=False, default=0)
    commit_count = Column(Integer, nullable=False, default=0)
    error_category = Column(String(20), nullable=True)
    error_message = Column(String(500), nullable=True)
    retry_after_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed')",
            name="ck_repo_sync_record_status",
        ),
        CheckConstraint(
            "error_category IS NULL OR error_category IN "
            "('auth', 'network', 'rate_limit', 'permission', 'other', 'interrupted')",
            name="ck_repo_sync_record_error_category",
        ),
        Index("ix_repo_sync_record_binding_started", "binding_id", "started_at"),
        MYSQL_TABLE_ARGS,
    )
