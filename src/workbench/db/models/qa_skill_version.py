from __future__ import annotations

from uuid import uuid4

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, medium_text, pk_type, utcnow

_VERSION_SOURCES = "('builtin', 'human', 'agent_proposal', 'rollback')"


class QaSkillVersion(Base):
    """QA 技能不可变版本历史。"""

    __tablename__ = "qa_skill_version"

    version_id = Column(CHAR(32), primary_key=True, default=lambda: uuid4().hex)
    skill_id = Column(
        CHAR(32),
        ForeignKey("qa_skill.skill_id", ondelete="CASCADE"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    content_md = Column(medium_text(), nullable=False)
    change_summary = Column(String(500), nullable=False)
    source_type = Column(String(32), nullable=False)
    approval_id = Column(CHAR(32), nullable=True)
    session_id = Column(pk_type(), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_qa_skill_version_num"),
        CheckConstraint(
            f"source_type IN {_VERSION_SOURCES}",
            name="ck_qa_skill_version_source",
        ),
        UniqueConstraint(
            "skill_id", "version", name="uq_qa_skill_version_skill_ver"
        ),
        MYSQL_TABLE_ARGS,
    )
