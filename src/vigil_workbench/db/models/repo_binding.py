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
    UniqueConstraint,
)

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow

_BINDING_STATUSES = "('unverified', 'connected', 'token_invalid', 'revoked')"
_VERIFY_RESULTS = "('success', 'auth-error', 'unreachable', 'permission-denied')"
_SYNC_STATUSES = "('success', 'failed')"
_ERROR_CATEGORIES = (
    "('auth', 'network', 'rate_limit', 'permission', 'other', 'interrupted')"
)


class RepoBinding(Base):
    """一行 = 一个只读绑定；解绑后保留（status='revoked'、active_flag=NULL）。"""

    __tablename__ = "repo_binding"

    binding_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider = Column(String(20), nullable=False)
    api_base_url = Column(String(255), nullable=False)
    org_id = Column(String(128), nullable=True)
    owner = Column(String(128), nullable=True)
    repo_id = Column(String(191), nullable=True)
    repo_name = Column(String(255), nullable=False)
    repo_key = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    default_branch = Column(String(255), nullable=True)
    token_ciphertext = Column(String(2048), nullable=True)
    token_masked = Column(String(64), nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default="unverified")
    active_flag = Column(CHAR(1), nullable=True, default="1")
    last_verified_at = Column(DateTime, nullable=True)
    last_verify_result = Column(String(20), nullable=True)
    last_verify_message = Column(String(500), nullable=True)
    last_sync_attempt_at = Column(DateTime, nullable=True)
    last_sync_status = Column(String(20), nullable=True)
    last_sync_success_at = Column(DateTime, nullable=True)
    last_sync_duration_ms = Column(Integer, nullable=True)
    last_sync_error_category = Column(String(20), nullable=True)
    last_sync_error_message = Column(String(500), nullable=True)
    last_sync_retry_after = Column(DateTime, nullable=True)
    sync_started_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "provider IN ('yunxiao', 'github')", name="ck_repo_binding_provider"
        ),
        CheckConstraint(
            f"status IN {_BINDING_STATUSES}", name="ck_repo_binding_status"
        ),
        CheckConstraint(
            "active_flag IS NULL OR active_flag = '1'",
            name="ck_repo_binding_active_flag",
        ),
        CheckConstraint(
            f"last_verify_result IS NULL OR last_verify_result IN {_VERIFY_RESULTS}",
            name="ck_repo_binding_last_verify_result",
        ),
        CheckConstraint(
            f"last_sync_status IS NULL OR last_sync_status IN {_SYNC_STATUSES}",
            name="ck_repo_binding_last_sync_status",
        ),
        CheckConstraint(
            "last_sync_error_category IS NULL OR "
            f"last_sync_error_category IN {_ERROR_CATEGORIES}",
            name="ck_repo_binding_last_sync_error_category",
        ),
        UniqueConstraint(
            "project_id",
            "provider",
            "repo_key",
            "active_flag",
            name="uq_repo_binding_project_provider_repo_active",
        ),
        Index("ix_repo_binding_project_status", "project_id", "status"),
        Index("ix_repo_binding_project_created", "project_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )
