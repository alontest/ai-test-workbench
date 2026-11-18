from __future__ import annotations

from sqlalchemy import JSON, CheckConstraint, Column, DateTime, ForeignKey, Index, String

from workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class SessionEvent(Base):
    __tablename__ = "session_event"

    event_id = Column(pk_type(), primary_key=True, autoincrement=True)
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    type = Column(String(32), nullable=False)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "type IN ('input_text', 'artifact', 'call', 'status_change', "
            "'knowledge_injection')",
            name="ck_session_event_type",
        ),
        Index("ix_session_event_session_id_event_id", "session_id", "event_id"),
        MYSQL_TABLE_ARGS,
    )
