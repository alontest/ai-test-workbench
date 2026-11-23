"""配置模块契约。用例名带 TC 编号，见 test-verification/tc-map.json。"""

from __future__ import annotations

import base64
import os

import pytest
from pydantic import ValidationError

from vigil_workbench.config import (
    ENCRYPTION_KEY_ENV,
    REPO_TOKEN_KEY_ENV,
    Settings,
    SettingsError,
)

TEST_KEY = base64.b64encode(bytes(range(32))).decode()
TEST_REPO_KEY = base64.b64encode(bytes(range(32, 64))).decode()


def _env(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> None:
    for name in (
        "VIGIL_ADMIN_PASSWORD",
        ENCRYPTION_KEY_ENV,
        REPO_TOKEN_KEY_ENV,
        "VIGIL_DATABASE_URL",
        "VIGIL_DATA_DIR",
        "VIGIL_PUBLIC_ORIGIN",
        "VIGIL_COOKIE_SECURE",
        "VIGIL_TRUST_PROXY",
        "VIGIL_ALLOW_REMOTE",
        "VIGIL_AI_MAX_CONCURRENCY",
        "VIGIL_PROMPT_MAX_CHARS",
    ):
        monkeypatch.delenv(name, raising=False)
    base = {
        "VIGIL_ADMIN_PASSWORD": "test-admin-pass",
        ENCRYPTION_KEY_ENV: TEST_KEY,
        REPO_TOKEN_KEY_ENV: TEST_REPO_KEY,
    }
    base.update(overrides)
    for name, value in base.items():
        if value is not None:
            monkeypatch.setenv(name, value)


def test_tc009_missing_admin_password_refuses_start(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, VIGIL_ADMIN_PASSWORD=None)
    with pytest.raises(SettingsError) as missing:
        Settings(_env_file=None)
    assert "VIGIL_ADMIN_PASSWORD" in str(missing.value)

    for blank in ("", "   "):
        _env(monkeypatch, VIGIL_ADMIN_PASSWORD=blank)
        with pytest.raises(SettingsError) as empty:
            Settings(_env_file=None)
        assert "VIGIL_ADMIN_PASSWORD" in str(empty.value)

    _env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.prompt_max_chars == 200000
    assert settings.ai_max_concurrency == 4


def test_tc057_frozen_settings_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.cookie_secure == "auto"
    assert settings.data_dir == "./data"
    assert settings.database_url is None
    assert settings.resolved_database_url.startswith("sqlite+aiosqlite:///")
    assert settings.resolved_database_url.endswith("vigil.db")
    assert settings.trust_proxy is False
    assert settings.allow_remote is False
    assert len(settings.encryption_key_bytes) == 32
    assert settings.public_origins == ("http://127.0.0.1:8000",)

    _env(monkeypatch, VIGIL_DATABASE_URL="mysql+asyncmy://u:p@db:3306/wb?charset=utf8mb4")
    assert Settings(_env_file=None).resolved_database_url.startswith("mysql+asyncmy://")

    _env(monkeypatch, VIGIL_PUBLIC_ORIGIN="http://a.test, https://b.test")
    assert Settings(_env_file=None).public_origins == ("http://a.test", "https://b.test")

    bad_keys = (
        base64.b64encode(b"short").decode(),
        "not-base64!!",
    )
    for bad in bad_keys:
        _env(monkeypatch, **{ENCRYPTION_KEY_ENV: bad})
        with pytest.raises(SettingsError) as err:
            Settings(_env_file=None)
        assert ENCRYPTION_KEY_ENV in str(err.value)
        assert bad not in str(err.value)

    _env(monkeypatch, VIGIL_COOKIE_SECURE="maybe")
    with pytest.raises(ValidationError) as err:
        Settings(_env_file=None)
    assert "VIGIL_COOKIE_SECURE" in str(err.value)


def test_tc009_settings_never_echo_secret_values(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "super-secret-admin"
    _env(monkeypatch, VIGIL_ADMIN_PASSWORD=secret, **{ENCRYPTION_KEY_ENV: "bad"})
    with pytest.raises(SettingsError) as err:
        Settings(_env_file=None)
    message = str(err.value)
    assert secret not in message
    assert os.environ["VIGIL_ADMIN_PASSWORD"] == secret
