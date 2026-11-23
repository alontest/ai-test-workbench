"""Declarative Base、命名约定与双方言类型助手。"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Integer, MetaData, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def pk_type() -> BigInteger:
    return BigInteger().with_variant(Integer, "sqlite")


def medium_text() -> Text:
    return Text().with_variant(mysql.MEDIUMTEXT(), "mysql")


def utcnow() -> datetime:
    """应用写 UTC naive 时间，禁止数据库时间函数。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)
