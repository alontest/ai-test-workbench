from __future__ import annotations

from sqlalchemy import CHAR, Column, DateTime, Index, String, UniqueConstraint

from workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class LoginSession(Base):
    __tablename__ = "login_session"

    login_session_id = Column(pk_type(), primary_key=True, autoincrement=True)
    token_hash = Column(CHAR(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=utcnow)
    revoked_at = Column(DateTime, nullable=True)
    source_ip_hash = Column(CHAR(64), nullable=True)

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_login_session_token_hash"),
        Index("ix_login_session_last_seen_at", "last_seen_at"),
        Index("ix_login_session_revoked_at", "revoked_at"),
        MYSQL_TABLE_ARGS,
    )
