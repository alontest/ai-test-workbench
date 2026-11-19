from __future__ import annotations

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

from workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow


class AiCallRecord(Base):
    __tablename__ = "ai_call_record"

    call_id = Column(pk_type(), primary_key=True, autoincrement=True)
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id = Column(
        pk_type(), ForeignKey("model_binding.model_id", ondelete="RESTRICT"), nullable=False
    )
    provider_id = Column(
        pk_type(),
        ForeignKey("provider_config.provider_id", ondelete="RESTRICT"),
        nullable=False,
    )
    model_name_snapshot = Column(String(191), nullable=False)
    display_name_snapshot = Column(String(191), nullable=False)
    provider_name_snapshot = Column(String(100), nullable=False)
    protocol_snapshot = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="running")
    prompt_digest = Column(CHAR(64), nullable=False)
    prompt_preview = Column(String(200), nullable=False)
    prompt_char_count = Column(Integer, nullable=False)
    knowledge_injection = Column(JSON, nullable=True)
    injected_chars = Column(Integer, nullable=False, default=0)
    prompt_chars = Column(Integer, nullable=False, default=0)
    total_chars = Column(Integer, nullable=False, default=0)
    result_text = Column(medium_text(), nullable=True)
    result_format = Column(String(16), nullable=False, default="text")
    latency_ms = Column(Integer, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    error_code = Column(String(32), nullable=True)
    error_message = Column(String(1000), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    finished_at = Column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'success', 'failed', 'timeout')",
            name="ck_ai_call_record_status",
        ),
        CheckConstraint(
            "retry_count >= 0 AND retry_count <= 1", name="ck_ai_call_record_retry_count"
        ),
        CheckConstraint(
            "prompt_char_count >= 0", name="ck_ai_call_record_prompt_char_count"
        ),
        CheckConstraint("injected_chars >= 0", name="ck_ai_call_record_injected_chars"),
        CheckConstraint("prompt_chars >= 0", name="ck_ai_call_record_prompt_chars"),
        CheckConstraint("total_chars >= 0", name="ck_ai_call_record_total_chars"),
        CheckConstraint(
            "total_chars = prompt_chars + injected_chars",
            name="ck_ai_call_record_total_chars_sum",
        ),
        Index("ix_ai_call_record_session_id_call_id", "session_id", "call_id"),
        Index("ix_ai_call_record_status_created_at", "status", "created_at"),
        Index("ix_ai_call_record_created_at", "created_at"),
        Index("ix_ai_call_record_model_id", "model_id"),
        Index("ix_ai_call_record_provider_id", "provider_id"),
        MYSQL_TABLE_ARGS,
    )
