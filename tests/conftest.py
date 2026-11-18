"""pytest 发现入口与共享夹具。用例名必须带 TC 编号。"""

from __future__ import annotations

import base64

import pytest
import pytest_asyncio

from workbench.config import ENCRYPTION_KEY_ENV, get_settings
from workbench.db.base import Base
from workbench.db.engine import Database, configure_database, create_engine_from_url

import workbench.db.models  # noqa: F401  注册全部模型

TEST_ADMIN_PASSWORD = "test-admin-pass"
TEST_ENCRYPTION_KEY = base64.b64encode(bytes(range(32))).decode()
TEST_PUBLIC_ORIGIN = "http://testserver"


@pytest.fixture
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("AW_ADMIN_PASSWORD", TEST_ADMIN_PASSWORD)
    monkeypatch.setenv(ENCRYPTION_KEY_ENV, TEST_ENCRYPTION_KEY)
    monkeypatch.setenv("AW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(
        "AW_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'workbench.db'}"
    )
    monkeypatch.setenv("AW_PUBLIC_ORIGIN", TEST_PUBLIC_ORIGIN)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def database(settings):
    engine = create_engine_from_url(settings.resolved_database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = Database(engine)
    configure_database(db)
    yield db
    configure_database(None)
    await db.dispose()


@pytest.fixture
def injection_preparer():
    """注册/注销假 InjectionPreparer。知识库实现属 knowledge-base spec。"""
    from fake_preparer import ScriptedInjectionPreparer
    from workbench.core.ports import register_injection_preparer

    impl = ScriptedInjectionPreparer()
    register_injection_preparer(impl)
    try:
        yield impl
    finally:
        register_injection_preparer(None)
