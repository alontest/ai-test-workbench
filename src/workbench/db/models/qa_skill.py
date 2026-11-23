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
    Integer,
    String,
    UniqueConstraint,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow

_SKILL_SCOPES = "('global', 'project')"
_SKILL_DOMAINS = (
    "('test-case', 'diagnosis', 'regression-list', 'test-report', 'general')"
)


class QaSkill(Base):
    """QA 技能主表；``scope_key + slug`` 跨双方言保证全局/项目唯一。"""

    __tablename__ = "qa_skill"

    skill_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    scope = Column(String(20), nullable=False)
    scope_key = Column(String(64), nullable=False)
    project_id = Column(
        pk_type(),
        ForeignKey("project_context.project_id", ondelete="CASCADE"),
        nullable=True,
    )
    slug = Column(String(100), nullable=False)
    name = Column(String(200), nullable=False)
    domain = Column(String(32), nullable=False, default="test-case")
    description = Column(String(500), nullable=False)
    triggers = Column(JSON, nullable=False)
    content_md = Column(medium_text(), nullable=False)
    current_version = Column(Integer, nullable=False, default=1)
    is_builtin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(f"scope IN {_SKILL_SCOPES}", name="ck_qa_skill_scope"),
        CheckConstraint(
            "(scope = 'global' AND project_id IS NULL) OR "
            "(scope = 'project' AND project_id IS NOT NULL)",
            name="ck_qa_skill_scope_project",
        ),
        CheckConstraint(f"domain IN {_SKILL_DOMAINS}", name="ck_qa_skill_domain"),
        CheckConstraint("current_version >= 1", name="ck_qa_skill_version"),
        UniqueConstraint("scope_key", "slug", name="uq_qa_skill_scope_slug"),
        Index("ix_qa_skill_project_domain", "project_id", "domain"),
        MYSQL_TABLE_ARGS,
    )
