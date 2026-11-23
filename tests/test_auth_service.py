"""认证服务：令牌哈希、失败锁定、空闲过期与登出。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from helpers import seed_admin
from vigil_workbench.core.constants import LOGIN_IDLE_TIMEOUT
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import LoginAttempt, LoginSession
from vigil_workbench.services import auth
from vigil_workbench.services.errors import DomainError

ADMIN = "test-admin-secret"


def _ip_hash(source_ip: str) -> str:
    return hashlib.sha256(source_ip.encode("utf-8")).hexdigest()


class Clock:
    def __init__(self) -> None:
        self.now = utcnow()

    def advance(self, delta: timedelta) -> None:
        self.now += delta


@pytest.mark.asyncio
async def test_tc001_unauthorized_without_session(database) -> None:
    sm = database.sessionmaker
    assert await auth.authenticate(None) is None
    assert await auth.authenticate("") is None
    assert await auth.authenticate("random-forged-token") is None
    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(LoginSession)) == 0


@pytest.mark.asyncio
async def test_tc002_login_issues_token_hash_only(database, settings) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)

    token, idle_expires_at = await auth.login(ADMIN, "10.0.0.1")
    assert token and len(token) >= 32
    assert idle_expires_at > utcnow()

    async with sm() as db:
        rows = (await db.scalars(select(LoginSession))).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert token not in row.token_hash
        assert row.revoked_at is None
        assert row.source_ip_hash == _ip_hash("10.0.0.1")

    refreshed = await auth.authenticate(token)
    assert refreshed is not None


@pytest.mark.asyncio
async def test_tc003_wrong_password_uniform_error(database, settings, caplog) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)

    caplog.set_level(logging.DEBUG)
    messages = set()
    for wrong in ("wrong-one", "wrong-two"):
        with pytest.raises(DomainError) as err:
            await auth.login(wrong, "10.0.0.2")
        assert err.value.code == "login_failed"
        assert err.value.status_code == 401
        messages.add(err.value.message)
        assert wrong not in str(err.value)
        assert wrong not in caplog.text
    assert len(messages) == 1

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(LoginSession)) == 0


@pytest.mark.asyncio
async def test_tc004_lock_after_five_failures(database, settings) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)
    clock = Clock()

    for _ in range(4):
        with pytest.raises(DomainError) as err:
            await auth.login("wrong", "10.0.0.3", now=clock.now)
        assert err.value.code == "login_failed"

    with pytest.raises(DomainError) as err:
        await auth.login("wrong", "10.0.0.3", now=clock.now)
    assert err.value.code == "login_failed"

    async with sm() as db:
        attempt = await db.get(LoginAttempt, _ip_hash("10.0.0.3"))
        assert attempt is not None
        assert attempt.failed_count == 5
        assert attempt.locked_until is not None

    # 锁定期内即使口令正确也 429，且不刷新计数。
    with pytest.raises(DomainError) as err:
        await auth.login(ADMIN, "10.0.0.3", now=clock.now + timedelta(minutes=4, seconds=59))
    assert err.value.code == "login_locked"
    assert err.value.status_code == 429
    retry_after = err.value.details[0]["retryAfterSeconds"]
    assert isinstance(retry_after, int) and retry_after > 0

    async with sm() as db:
        attempt = await db.get(LoginAttempt, _ip_hash("10.0.0.3"))
        assert attempt.failed_count == 5

    # 5 分钟后允许重新校验，成功登录删除计数行。
    token, _ = await auth.login(ADMIN, "10.0.0.3", now=clock.now + timedelta(minutes=5))
    assert token
    async with sm() as db:
        assert await db.get(LoginAttempt, _ip_hash("10.0.0.3")) is None

    # 其他来源 IP 不共享计数。
    with pytest.raises(DomainError) as err:
        await auth.login("wrong", "10.0.0.4", now=clock.now)
    assert err.value.code == "login_failed"


@pytest.mark.asyncio
async def test_tc005_concurrent_failures_counted(database, settings) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)

    async def attempt() -> str:
        try:
            await auth.login("wrong", "10.0.0.5")
        except DomainError as exc:
            return exc.code
        return "ok"

    results = await asyncio.gather(*(attempt() for _ in range(6)))
    assert set(results) <= {"login_failed", "login_locked"}
    assert "login_locked" in results

    async with sm() as db:
        row = await db.get(LoginAttempt, _ip_hash("10.0.0.5"))
        assert row is not None and row.failed_count >= 5
        assert await db.scalar(select(func.count()).select_from(LoginSession)) == 0


@pytest.mark.asyncio
async def test_tc006_idle_expiry_and_refresh(database, settings) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)
    clock = Clock()
    token, _ = await auth.login(ADMIN, "10.0.0.6", now=clock.now)

    clock.advance(timedelta(hours=7, minutes=59))
    session = await auth.authenticate(token, now=clock.now)
    assert session is not None
    first_seen = session.last_seen_at
    assert first_seen == clock.now

    clock.advance(timedelta(hours=7, minutes=59))
    assert await auth.authenticate(token, now=clock.now) is not None
    active_at = clock.now

    clock.advance(LOGIN_IDLE_TIMEOUT + timedelta(seconds=1))
    assert await auth.authenticate(token, now=clock.now) is None

    async with sm() as db:
        row = await db.get(LoginSession, session.login_session_id)
        assert row.last_seen_at == active_at


@pytest.mark.asyncio
async def test_tc007_logout_revokes_token(database, settings) -> None:
    sm = database.sessionmaker
    await seed_admin(sm, ADMIN)
    token, _ = await auth.login(ADMIN, "10.0.0.7")

    assert await auth.logout(token) is True
    assert await auth.authenticate(token) is None
    async with sm() as db:
        row = (await db.scalars(select(LoginSession))).one()
        assert row.revoked_at is not None

    assert await auth.logout(token) is False
