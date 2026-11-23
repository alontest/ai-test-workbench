from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow

_PLAN_STATUSES = "('draft', 'generated')"


class TestCaseDesignPlan(Base):
    """阶段 1：测试设计检查点矩阵。"""

    __test__ = False
    __tablename__ = "test_case_design_plan"

    plan_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    call_id = Column(pk_type(), nullable=True)
    skill_id = Column(CHAR(32), nullable=True)
    skill_version = Column(Integer, nullable=True)
    title = Column(String(200), nullable=False)
    requirement_text = Column(medium_text(), nullable=False)
    checkpoints = Column(JSON, nullable=False)
    kb_links = Column(JSON, nullable=False)
    code_paths = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="draft")
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            f"status IN {_PLAN_STATUSES}",
            name="ck_test_case_design_plan_status",
        ),
        Index(
            "ix_test_case_design_plan_project_created",
            "project_id",
            "created_at",
        ),
        MYSQL_TABLE_ARGS,
    )
