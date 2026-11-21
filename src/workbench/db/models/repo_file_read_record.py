from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, utcnow


class RepoFileReadRecord(Base):
    """一行 = 一次按需读取审计；只存元数据，不存文件正文。"""

    __tablename__ = "repo_file_read_record"

    read_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    binding_id = Column(
        CHAR(32),
        ForeignKey("repo_binding.binding_id", ondelete="CASCADE"),
        nullable=False,
    )
    repo_id = Column(String(191), nullable=False)
    ref = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    byte_size = Column(BigInteger, nullable=True)
    encoding = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)
    reject_reason = Column(String(20), nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint(
            "encoding IN ('text', 'base64')",
            name="ck_repo_file_read_record_encoding",
        ),
        CheckConstraint(
            "status IN ('success', 'refused')",
            name="ck_repo_file_read_record_status",
        ),
        CheckConstraint(
            "reject_reason IS NULL OR reject_reason IN "
            "('too_large', 'binary', 'not_utf8')",
            name="ck_repo_file_read_record_reject_reason",
        ),
        Index(
            "ix_repo_file_read_record_binding_fetched",
            "binding_id",
            "fetched_at",
        ),
        MYSQL_TABLE_ARGS,
    )
