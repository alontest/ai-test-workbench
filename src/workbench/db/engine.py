"""双方言引擎与会话工厂。"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool, StaticPool, Pool

MYSQL_POOL_SIZE = 5
MYSQL_MAX_OVERFLOW = 5
MYSQL_POOL_RECYCLE_SECONDS = 1800
MYSQL_POOL_TIMEOUT_SECONDS = 10
SQLITE_BUSY_TIMEOUT_MS = 5000


def _install_sqlite_pragmas(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
        finally:
            cursor.close()


def create_engine_from_url(url: str, *, echo: bool = False) -> AsyncEngine:
    if url.startswith("sqlite"):
        poolclass: type[Pool]
        connect_args: dict[str, object] = {"timeout": SQLITE_BUSY_TIMEOUT_MS / 1000}
        if ":memory:" in url or url.endswith("://"):
            poolclass = StaticPool
        else:
            poolclass = NullPool
        engine = create_async_engine(
            url,
            echo=echo,
            poolclass=poolclass,
            connect_args=connect_args,
        )
        _install_sqlite_pragmas(engine)
        return engine
    return create_async_engine(
        url,
        echo=echo,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=MYSQL_POOL_SIZE,
        max_overflow=MYSQL_MAX_OVERFLOW,
        pool_recycle=MYSQL_POOL_RECYCLE_SECONDS,
        pool_pre_ping=True,
        pool_timeout=MYSQL_POOL_TIMEOUT_SECONDS,
        isolation_level="READ COMMITTED",
    )


@dataclass
class Database:
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession] = field(init=False)

    def __post_init__(self) -> None:
        self.sessionmaker = async_sessionmaker(
            self.engine, expire_on_commit=False, autoflush=False
        )

    async def dispose(self) -> None:
        await self.engine.dispose()


_database: Database | None = None


def configure_database(database: Database | None) -> None:
    global _database
    _database = database


def get_database() -> Database:
    if _database is None:
        raise RuntimeError("数据库尚未初始化")
    return _database


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return get_database().sessionmaker
