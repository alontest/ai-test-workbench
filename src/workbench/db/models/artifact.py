from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class Artifact(Base):
    __tablename__ = "artifact"

    artifact_id = Column(pk_type(), primary_key=True, autoincrement=True)
    session_id = Column(
        pk_type(),
        ForeignKey("analysis_session.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    kind = Column(String(16), nullable=False, default="upload")
    file_name = Column(String(255), nullable=False)
    file_name_key = Column(
        String(255).with_variant(String(255, collation="utf8mb4_bin"), "mysql"),
        nullable=False,
    )
    storage_name = Column(String(120), nullable=False)
    relative_path = Column(String(300), nullable=False)
    mime_type = Column(String(100), nullable=False)
    byte_size = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("kind IN ('upload', 'generated')", name="ck_artifact_kind"),
        CheckConstraint("byte_size >= 0", name="ck_artifact_byte_size"),
        UniqueConstraint(
            "session_id", "file_name_key", name="uq_artifact_session_id_file_name_key"
        ),
        UniqueConstraint(
            "session_id", "storage_name", name="uq_artifact_session_id_storage_name"
        ),
        Index("ix_artifact_session_id_created_at", "session_id", "created_at"),
        MYSQL_TABLE_ARGS,
    )
