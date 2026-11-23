"""认证：口令登录、令牌哈希、失败锁定与空闲过期（ADR-021 / ADR-025）。"""

from __future__ import annotations

import hashlib
import math
import secrets
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.core.constants import (
    LOGIN_FAILURE_WINDOW,
    LOGIN_IDLE_TIMEOUT,
    LOGIN_LOCK_DURATION,
    LOGIN_MAX_FAILURES,
)
from vigil_workbench.core.passwords import verify_password
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.errors import is_unique_violation
from vigil_workbench.db.models import AdminCredential, LoginAttempt, LoginSession
from vigil_workbench.services.errors import DomainError

TOKEN_BYTES = 32
_GENERIC_FAILURE_MESSAGE = "口令错误，请重试。"
_LOCKED_MESSAGE = "尝试次数过多，请稍后再试。"
_MAX_WRITE_RETRIES = 3


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def attempt_key(source_ip: str | None) -> str:
    """来源 IP 只以 SHA-256 十六进制落库，不存原文。"""
    return hashlib.sha256((source_ip or "").encode("utf-8")).hexdigest()


async def login(
    password: str,
    source_ip: str | None,
    *,
    now: datetime | None = None,
) -> tuple[str, datetime]:
    """校验口令并签发令牌；返回 (token, idle 过期时间)。"""
    moment = now or utcnow()
    key = attempt_key(source_ip)
    sessionmaker = get_sessionmaker()

    async with sessionmaker() as db:
        attempt = await db.get(LoginAttempt, key)
        if attempt is not None and attempt.locked_until is not None:
            if moment < attempt.locked_until:
                seconds = max(
                    1, math.ceil((attempt.locked_until - moment).total_seconds())
                )
                raise DomainError(
                    "login_locked",
                    _LOCKED_MESSAGE,
                    status_code=429,
                    details=[{"retryAfterSeconds": seconds}],
                    headers={"Retry-After": str(seconds)},
                )

        credential = await db.get(AdminCredential, 1)
        valid = credential is not None and verify_password(
            credential.password_hash, password
        )
        if not valid:
            locked, count = await _record_failure(db, key, moment)
            if locked and count > LOGIN_MAX_FAILURES:
                seconds = int(LOGIN_LOCK_DURATION.total_seconds())
                raise DomainError(
                    "login_locked",
                    _LOCKED_MESSAGE,
                    status_code=429,
                    details=[{"retryAfterSeconds": seconds}],
                    headers={"Retry-After": str(seconds)},
                )
            raise DomainError("login_failed", _GENERIC_FAILURE_MESSAGE, status_code=401)

        await db.execute(delete(LoginAttempt).where(LoginAttempt.source_ip_hash == key))
        token = secrets.token_urlsafe(TOKEN_BYTES)
        db.add(
            LoginSession(
                token_hash=hash_token(token),
                created_at=moment,
                last_seen_at=moment,
                source_ip_hash=key,
            )
        )
        await db.commit()

    return token, moment + LOGIN_IDLE_TIMEOUT


async def authenticate(token: str | None, *, now: datetime | None = None) -> LoginSession | None:
    """校验令牌并刷新 last_seen_at；过期或吊销返回 None。"""
    if not token:
        return None
    moment = now or utcnow()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.scalar(
            select(LoginSession).where(
                LoginSession.token_hash == hash_token(token),
                LoginSession.revoked_at.is_(None),
            )
        )
        if row is None:
            return None
        if moment - row.last_seen_at > LOGIN_IDLE_TIMEOUT:
            return None
        row.last_seen_at = moment
        await db.commit()
        return row


async def logout(token: str | None, *, now: datetime | None = None) -> bool:
    """吊销令牌；无有效会话返回 False。"""
    if not token:
        return False
    moment = now or utcnow()
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.scalar(
            select(LoginSession).where(
                LoginSession.token_hash == hash_token(token),
                LoginSession.revoked_at.is_(None),
            )
        )
        if row is None:
            return False
        row.revoked_at = moment
        await db.commit()
        return True


async def _record_failure(db: AsyncSession, key: str, now: datetime) -> bool:
    """原子自增失败计数；达到阈值写 locked_until（双方言同一实现）。"""
    for attempt in range(_MAX_WRITE_RETRIES):
        try:
            return await _record_failure_once(db, key, now)
        except DBAPIError as exc:
            await db.rollback()
            locked = "database is locked" in str(getattr(exc, "orig", exc)).lower()
            if not locked or attempt == _MAX_WRITE_RETRIES - 1:
                raise
    return False, 0


async def _record_failure_once(db: AsyncSession, key: str, now: datetime) -> tuple[bool, int]:
    window_start = now - LOGIN_FAILURE_WINDOW
    outside_window = LoginAttempt.last_failed_at < window_start
    update_stmt = (
        update(LoginAttempt)
        .where(LoginAttempt.source_ip_hash == key)
        .values(
            failed_count=_case(outside_window, 1, LoginAttempt.failed_count + 1),
            first_failed_at=_case(outside_window, now, LoginAttempt.first_failed_at),
            last_failed_at=now,
        )
    )
    result = await db.execute(update_stmt)
    if not result.rowcount:
        db.add(
            LoginAttempt(
                source_ip_hash=key,
                failed_count=1,
                first_failed_at=now,
                last_failed_at=now,
            )
        )
        try:
            await db.commit()
            return False, 1
        except DBAPIError as exc:
            await db.rollback()
            if not is_unique_violation(exc):
                raise
            result = await db.execute(update_stmt)
            if not result.rowcount:
                return False, 0

    count = await db.scalar(
        select(LoginAttempt.failed_count).where(LoginAttempt.source_ip_hash == key)
    )
    locked = count is not None and count >= LOGIN_MAX_FAILURES
    if locked:
        await db.execute(
            update(LoginAttempt)
            .where(LoginAttempt.source_ip_hash == key)
            .values(locked_until=now + LOGIN_LOCK_DURATION)
        )
    await db.commit()
    return locked, count or 0


def _case(condition, when_true, when_false):  # noqa: ANN001, ANN202
    from sqlalchemy import case

    return case((condition, when_true), else_=when_false)
