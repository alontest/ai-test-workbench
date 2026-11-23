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

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow

_TARGET_TYPES = "('qa_skill')"
_ACTION_TYPES = "('update_skill', 'create_skill')"
_APPROVAL_STATUSES = "('pending', 'approved', 'rejected')"


class ApprovalRequest(Base):
    """轻量审批单（Human-in-the-Loop 闸门）。"""

    __tablename__ = "approval_request"

    approval_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="CASCADE"),
        nullable=True,
    )
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="SET NULL"),
        nullable=True,
    )
    call_id = Column(pk_type(), nullable=True)
    target_type = Column(String(32), nullable=False, default="qa_skill")
    target_id = Column(CHAR(32), nullable=False)
    target_title = Column(String(200), nullable=False)
    action_type = Column(String(32), nullable=False)
    base_version = Column(Integer, nullable=False)
    before_content = Column(medium_text(), nullable=False)
    after_content = Column(medium_text(), nullable=False)
    unified_diff = Column(medium_text(), nullable=False)
    rationale = Column(String(1000), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    decision_note = Column(String(500), nullable=True)
    applied_version = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    decided_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"target_type IN {_TARGET_TYPES}",
            name="ck_approval_request_target_type",
        ),
        CheckConstraint(
            f"action_type IN {_ACTION_TYPES}",
            name="ck_approval_request_action_type",
        ),
        CheckConstraint(
            f"status IN {_APPROVAL_STATUSES}",
            name="ck_approval_request_status",
        ),
        CheckConstraint(
            "base_version >= 0",
            name="ck_approval_request_base_version",
        ),
        Index("ix_approval_request_status_created", "status", "created_at"),
        Index("ix_approval_request_project_created", "project_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )
