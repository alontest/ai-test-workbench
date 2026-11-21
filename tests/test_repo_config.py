"""仓库令牌独立密钥的启动期校验。用例名带 TC 编号。"""

from __future__ import annotations

import base64

import pytest

from workbench.config import (
    ENCRYPTION_KEY_ENV,
    REPO_TOKEN_KEY_ENV,
    Settings,
    SettingsError,
)

ADMIN_ENV = "AW_ADMIN_PASSWORD"
MODEL_KEY = base64.b64encode(bytes(range(32))).decode()
REPO_KEY = base64.b64encode(bytes(range(32, 64))).decode()


def _env(monkeypatch: pytest.MonkeyPatch, **overrides: str | None) -> None:
    for name in (ADMIN_ENV, ENCRYPTION_KEY_ENV, REPO_TOKEN_KEY_ENV):
        monkeypatch.delenv(name, raising=False)
    values = {
        ADMIN_ENV: "test-admin-pass",
        ENCRYPTION_KEY_ENV: MODEL_KEY,
        REPO_TOKEN_KEY_ENV: REPO_KEY,
    }
    values.update(overrides)
    for name, value in values.items():
        if value is not None:
            monkeypatch.setenv(name, value)


def test_tc248_repo_token_key_required_and_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, **{REPO_TOKEN_KEY_ENV: None})
    with pytest.raises(SettingsError) as missing:
        Settings(_env_file=None)
    assert REPO_TOKEN_KEY_ENV in str(missing.value)

    for bad in (
        "not-base64!!",
        base64.b64encode(b"short").decode(),
        base64.b64encode(bytes(range(31))).decode(),
        base64.b64encode(bytes(range(64))).decode(),
    ):
        _env(monkeypatch, **{REPO_TOKEN_KEY_ENV: bad})
        with pytest.raises(SettingsError) as err:
            Settings(_env_file=None)
        message = str(err.value)
        assert REPO_TOKEN_KEY_ENV in message
        assert bad not in message

    _env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.repo_token_key_bytes == bytes(range(32, 64))
    assert settings.encryption_key_bytes == bytes(range(32))
    assert settings.repo_token_key_bytes != settings.encryption_key_bytes

    assert REPO_TOKEN_KEY_ENV not in repr(settings)
    assert REPO_KEY not in repr(settings)


def test_tc248_model_key_unchanged_when_repo_key_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _env(monkeypatch, **{REPO_TOKEN_KEY_ENV: "bad"})
    with pytest.raises(SettingsError):
        Settings(_env_file=None)

    _env(monkeypatch, **{REPO_TOKEN_KEY_ENV: base64.b64encode(b"x").decode()})
    with pytest.raises(SettingsError) as err:
        Settings(_env_file=None)
    assert MODEL_KEY not in str(err.value)
