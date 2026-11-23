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

_PRIORITIES = "('P0', 'P1', 'P2', 'P3')"
_CASE_TYPES = "('functional', 'boundary', 'exception', 'security', 'concurrency')"


class TestCase(Base):
    """阶段 2：结构化测试用例库。"""

    __test__ = False
    __tablename__ = "test_case"

    case_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id = Column(
        CHAR(32),
        ForeignKey("test_case_design_plan.plan_id", ondelete="SET NULL"),
        nullable=True,
    )
    checkpoint_id = Column(String(64), nullable=True)
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="SET NULL"),
        nullable=True,
    )
    call_id = Column(pk_type(), nullable=True)
    skill_id = Column(CHAR(32), nullable=True)
    skill_version = Column(Integer, nullable=True)
    case_code = Column(String(64), nullable=False)
    module = Column(String(120), nullable=False)
    title = Column(String(300), nullable=False)
    priority = Column(String(16), nullable=False, default="P1")
    case_type = Column(String(32), nullable=False, default="functional")
    preconditions = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)
    expected_summary = Column(medium_text(), nullable=False)
    kb_links = Column(JSON, nullable=False)
    code_paths = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            f"priority IN {_PRIORITIES}", name="ck_test_case_priority"
        ),
        CheckConstraint(
            f"case_type IN {_CASE_TYPES}", name="ck_test_case_type"
        ),
        Index("ix_test_case_project_module", "project_id", "module"),
        Index("ix_test_case_project_updated", "project_id", "updated_at"),
        MYSQL_TABLE_ARGS,
    )
