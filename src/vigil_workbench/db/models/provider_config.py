from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, String

from vigil_workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class ProviderConfig(Base):
    __tablename__ = "provider_config"

    provider_id = Column(pk_type(), primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    protocol = Column(String(32), nullable=False)
    base_url = Column(String(500), nullable=False)
    api_key_ciphertext = Column(String(1024), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "protocol IN ('openai_compatible', 'anthropic')",
            name="ck_provider_config_protocol",
        ),
        Index("ix_provider_config_enabled", "enabled"),
        MYSQL_TABLE_ARGS,
    )
