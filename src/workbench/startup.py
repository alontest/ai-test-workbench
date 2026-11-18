"""启动自检与后台清理（ADR-020）。"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from workbench.core.passwords import hash_password, verify_password
from workbench.core.constants import (
    LOGIN_ATTEMPT_RETENTION,
    LOGIN_SESSION_RETENTION,
)
from workbench.db.base import utcnow
from workbench.db.models import (
    AdminCredential,
    AiCallRecord,
    AnalysisSession,
    LoginAttempt,
    LoginSession,
    SessionEvent,
)
from workbench.services.sessions import append_event_in_db

logger = logging.getLogger(__name__)

HEAD_REVISION = "0006"
DATABASE_CONNECT_TIMEOUT_SECONDS = 30
DATABASE_CONNECT_RETRY_INTERVAL_SECONDS = 1.0


class StartupError(RuntimeError):
    """启动自检失败；调用方转成非 0 退出。"""


async def wait_for_database(database, timeout: float = DATABASE_CONNECT_TIMEOUT_SECONDS) -> None:  # noqa: ANN001
    deadline = asyncio.get_running_loop().time() + timeout
    last_error: Exception | None = None
    while True:
        try:
            async with database.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # 连接期失败按退避重试
            last_error = exc
        if asyncio.get_running_loop().time() >= deadline:
            raise StartupError("数据库连接失败") from last_error
        await asyncio.sleep(DATABASE_CONNECT_RETRY_INTERVAL_SECONDS)


async def ensure_admin_credential(sessionmaker, password: str) -> None:
    if not password.strip():
        raise StartupError("AW_ADMIN_PASSWORD 为空")
    async with sessionmaker() as db:
        row = await db.get(AdminCredential, 1)
        now = utcnow()
        if row is None:
            db.add(
                AdminCredential(
                    credential_id=1,
                    algorithm="argon2id",
                    password_hash=hash_password(password),
                    updated_at=now,
                )
            )
        elif not verify_password(row.password_hash, password):
            row.password_hash = hash_password(password)
            row.algorithm = "argon2id"
            row.updated_at = now
        await db.commit()


async def verify_migration_head(sessionmaker) -> None:
    async with sessionmaker() as db:
        try:
            version = await db.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception as exc:  # 表不存在等
            raise StartupError("数据库未迁移到 head") from exc
    if version != HEAD_REVISION:
        raise StartupError(f"数据库版本 {version} 不是 {HEAD_REVISION}")


async def merge_running_calls(sessionmaker) -> int:
    """把所有遗留 running 调用终结为 failed(interrupted)，并追加 call 事件。"""
    async with sessionmaker() as db:
        rows = (
            await db.scalars(
                select(AiCallRecord).where(AiCallRecord.status == "running")
            )
        ).all()
        if not rows:
            return 0
        now = utcnow()
        for record in rows:
            latency_ms = max(
                0, int((now - record.created_at).total_seconds() * 1000)
            )
            record.status = "failed"
            record.error_code = "interrupted"
            record.error_message = "service restarted before completion"
            record.finished_at = now
            record.latency_ms = latency_ms
            session = await db.get(AnalysisSession, record.session_id)
            if session is not None:
                await append_event_in_db(
                    db,
                    session,
                    "call",
                    {
                        "callId": record.call_id,
                        "modelId": record.model_id,
                        "modelDisplayName": record.display_name_snapshot,
                        "status": "failed",
                        "latencyMs": latency_ms,
                        "retryCount": record.retry_count,
                        "promptPreview": record.prompt_preview,
                        "errorCode": "interrupted",
                    },
                    actor="system",
                )
        await db.commit()
        logger.info("merged %d running ai calls", len(rows))
        return len(rows)


async def cleanup_expired(sessionmaker, now=None) -> int:  # noqa: ANN001
    current = now or utcnow()
    removed = 0
    async with sessionmaker() as db:
        session_cutoff = current - LOGIN_SESSION_RETENTION
        attempt_cutoff = current - LOGIN_ATTEMPT_RETENTION
        result = await db.execute(
            delete(LoginSession).where(
                (LoginSession.last_seen_at < session_cutoff)
                | (LoginSession.revoked_at < session_cutoff)
            )
        )
        removed += result.rowcount or 0
        result = await db.execute(
            delete(LoginAttempt).where(LoginAttempt.last_failed_at < attempt_cutoff)
        )
        removed += result.rowcount or 0
        await db.commit()
    return removed


async def run_startup(database, settings) -> None:  # noqa: ANN001
    """ADR-020 顺序：连接 → 管理员口令 → 迁移版本 → 归并 → 清理。"""
    await wait_for_database(database)
    await ensure_admin_credential(database.sessionmaker, settings.admin_password_value)
    await verify_migration_head(database.sessionmaker)
    await merge_running_calls(database.sessionmaker)
    await cleanup_expired(database.sessionmaker)


def main() -> int:
    """容器入口的启动自检；任何一步失败都以非 0 退出。"""
    from workbench.config import SettingsError, get_settings
    from workbench.db.engine import Database, create_engine_from_url

    logging.basicConfig(level=logging.INFO)
    try:
        settings = get_settings()
    except SettingsError as exc:
        logging.error("启动配置非法：%s", exc)
        return 2

    async def _run() -> None:
        database = Database(create_engine_from_url(settings.resolved_database_url))
        try:
            await run_startup(database, settings)
        finally:
            await database.dispose()

    try:
        asyncio.run(_run())
    except StartupError as exc:
        logging.error("启动自检失败：%s", exc)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - 入口
    raise SystemExit(main())
