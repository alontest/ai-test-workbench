from __future__ import annotations

from sqlalchemy import Column, DateTime, Index, String, UniqueConstraint

from workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow


class ProjectContext(Base):
    __tablename__ = "project_context"

    project_id = Column(pk_type(), primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    name_key = Column(
        String(100).with_variant(String(100, collation="utf8mb4_bin"), "mysql"),
        nullable=False,
    )
    repo_url = Column(String(500), nullable=True)
    tech_stack = Column(String(500), nullable=True)
    requirement_source = Column(medium_text(), nullable=True)
    notes = Column(medium_text(), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("name_key", name="uq_project_context_name_key"),
        Index("ix_project_context_updated_at", "updated_at"),
        MYSQL_TABLE_ARGS,
    )
