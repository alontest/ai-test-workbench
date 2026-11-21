from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class KnowledgeBase(Base):
    """一行 = 一个版本快照；``project_id + name_key`` 构成逻辑库。"""

    __tablename__ = "knowledge_base"

    kb_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="RESTRICT"),
        nullable=False,
    )
    name = Column(String(200), nullable=False)
    name_key = Column(String(200), nullable=False)
    version = Column(Integer, nullable=False)
    current_flag = Column(CHAR(1), nullable=True)
    status = Column(String(20), nullable=False, default="ready")
    index_generated_at = Column(DateTime, nullable=True)
    entry_count = Column(Integer, nullable=False, default=0)
    file_count = Column(Integer, nullable=False, default=0)
    total_byte_size = Column(BigInteger, nullable=False, default=0)
    source_index_sha256 = Column(CHAR(64), nullable=False)
    storage_dir = Column(String(191), nullable=False)
    superseded_by_kb_id = Column(CHAR(32), nullable=True)
    import_report = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "current_flag IS NULL OR current_flag = '1'",
            name="ck_knowledge_base_current_flag",
        ),
        CheckConstraint(
            "status IN ('ready', 'superseded')", name="ck_knowledge_base_status"
        ),
        CheckConstraint("version >= 1", name="ck_knowledge_base_version"),
        CheckConstraint("entry_count >= 0", name="ck_knowledge_base_entry_count"),
        CheckConstraint("file_count >= 0", name="ck_knowledge_base_file_count"),
        CheckConstraint(
            "total_byte_size >= 0", name="ck_knowledge_base_total_byte_size"
        ),
        UniqueConstraint(
            "project_id",
            "name_key",
            "current_flag",
            name="uq_knowledge_base_project_name_current",
        ),
        UniqueConstraint(
            "project_id",
            "name_key",
            "version",
            name="uq_knowledge_base_project_name_version",
        ),
        Index("ix_knowledge_base_project_current", "project_id", "current_flag"),
        Index("ix_knowledge_base_project_name", "project_id", "name_key"),
        MYSQL_TABLE_ARGS,
    )
