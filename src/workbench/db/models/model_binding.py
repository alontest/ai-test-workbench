from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from workbench.db.base import Base, MYSQL_TABLE_ARGS, pk_type, utcnow


class ModelBinding(Base):
    __tablename__ = "model_binding"

    model_id = Column(pk_type(), primary_key=True, autoincrement=True)
    provider_id = Column(
        pk_type(), ForeignKey("provider_config.provider_id", ondelete="RESTRICT"), nullable=False
    )
    model_name = Column(String(191), nullable=False)
    model_name_key = Column(
        String(191).with_variant(String(191, collation="utf8mb4_bin"), "mysql"),
        nullable=False,
    )
    display_name = Column(String(191), nullable=False)
    default_temperature = Column(Numeric(3, 2), nullable=False, default=0.70)
    default_max_tokens = Column(Integer, nullable=False, default=4096)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "provider_id",
            "model_name_key",
            name="uq_model_binding_provider_id_model_name_key",
        ),
        CheckConstraint(
            "default_temperature >= 0 AND default_temperature <= 2",
            name="ck_model_binding_default_temperature",
        ),
        CheckConstraint(
            "default_max_tokens > 0 AND default_max_tokens <= 1000000",
            name="ck_model_binding_default_max_tokens",
        ),
        Index("ix_model_binding_provider_id_enabled", "provider_id", "enabled"),
        MYSQL_TABLE_ARGS,
    )
