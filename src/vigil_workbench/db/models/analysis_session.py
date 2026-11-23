from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow

ENTRANCE_KEYS_SQL = (
    "'case-library', 'bug-analysis', 'log-triage', "
    "'sql-analysis', 'regression-list', 'test-report'"
)


class AnalysisSession(Base):
    __tablename__ = "analysis_session"

    session_id = Column(pk_type(), primary_key=True, autoincrement=True)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="RESTRICT"),
        nullable=False,
    )
    entrance_key = Column(String(32), nullable=False)
    title = Column(String(200), nullable=False)
    status = Column(String(16), nullable=False, default="in_progress")
    model_id = Column(
        pk_type(), ForeignKey("model_binding.model_id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow)
    closed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"entrance_key IN ({ENTRANCE_KEYS_SQL})",
            name="ck_analysis_session_entrance_key",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed')",
            name="ck_analysis_session_status",
        ),
        Index("ix_analysis_session_project_id_updated_at", "project_id", "updated_at"),
        Index("ix_analysis_session_status_updated_at", "status", "updated_at"),
        Index("ix_analysis_session_updated_at", "updated_at"),
        Index("ix_analysis_session_model_id", "model_id"),
        MYSQL_TABLE_ARGS,
    )
