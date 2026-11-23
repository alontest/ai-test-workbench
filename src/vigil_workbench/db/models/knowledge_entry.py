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
    UniqueConstraint,
)

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, utcnow


class KnowledgeEntry(Base):
    """一行 = 一个编号；删除知识库时级联删除。"""

    __tablename__ = "knowledge_entry"

    entry_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    kb_id = Column(
        CHAR(32),
        ForeignKey("knowledge_base.kb_id", ondelete="CASCADE"),
        nullable=False,
    )
    code = Column(String(128), nullable=False)
    code_key = Column(String(128), nullable=False)
    type = Column(String(20), nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(medium_text(), nullable=False, default="")
    body = Column(medium_text(), nullable=True)
    body_missing = Column(Boolean, nullable=False, default=True)
    body_source_file = Column(String(255), nullable=True)
    fields = Column(JSON, nullable=True)
    tables = Column(JSON, nullable=True)
    code_paths = Column(JSON, nullable=True)
    neighbors = Column(JSON, nullable=True)
    extras = Column(JSON, nullable=True)
    source_doc = Column(String(100), nullable=True)
    anchor = Column(String(200), nullable=True)
    freshness_at = Column(DateTime, nullable=True)
    content_digest = Column(CHAR(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "type IN ('term', 'entity', 'state', 'rule', 'process', 'api', "
            "'domain_event', 'other')",
            name="ck_knowledge_entry_type",
        ),
        UniqueConstraint("kb_id", "code_key", name="uq_knowledge_entry_kb_code"),
        Index("ix_knowledge_entry_code_key", "code_key"),
        Index("ix_knowledge_entry_kb_type", "kb_id", "type"),
        MYSQL_TABLE_ARGS,
    )
