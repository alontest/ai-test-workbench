from __future__ import annotations

from sqlalchemy import CheckConstraint, Column, DateTime, SmallInteger, String

from workbench.db.base import Base, MYSQL_TABLE_ARGS, utcnow


class AdminCredential(Base):
    __tablename__ = "admin_credential"

    credential_id = Column(SmallInteger, primary_key=True, default=1)
    algorithm = Column(String(32), nullable=False, default="argon2id")
    password_hash = Column(String(255), nullable=False)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint("credential_id = 1", name="ck_admin_credential_credential_id"),
        MYSQL_TABLE_ARGS,
    )
