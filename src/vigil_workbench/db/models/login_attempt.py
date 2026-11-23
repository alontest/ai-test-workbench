from __future__ import annotations

from sqlalchemy import CHAR, Column, DateTime, Index, Integer

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS


class LoginAttempt(Base):
    __tablename__ = "login_attempt"

    source_ip_hash = Column(CHAR(64), primary_key=True)
    failed_count = Column(Integer, nullable=False, default=0)
    first_failed_at = Column(DateTime, nullable=True)
    last_failed_at = Column(DateTime, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_login_attempt_last_failed_at", "last_failed_at"),
        MYSQL_TABLE_ARGS,
    )
