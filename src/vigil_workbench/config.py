"""VIGIL_* 环境变量与启动期校验。

缺失或非法配置在构造 ``Settings`` 时立即失败；调用方（startup）把它转成
非 0 退出。错误信息只提变量名，不回显变量值。
"""

from __future__ import annotations

import base64
import binascii
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENCRYPTION_KEY_ENV = "VIGIL_ENCRYPTION_KEY"
REPO_TOKEN_KEY_ENV = "VIGIL_REPO_TOKEN_KEY"

_COOKIE_SECURE_VALUES = ("auto", "true", "false")


class SettingsError(RuntimeError):
    """启动期环境变量缺失或非法。"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VIGIL_",
        case_sensitive=False,
        extra="ignore",
    )

    admin_password: SecretStr | None = Field(
        default=None, validation_alias="VIGIL_ADMIN_PASSWORD"
    )
    encryption_key: SecretStr | None = Field(default=None, validation_alias=ENCRYPTION_KEY_ENV)
    repo_token_key: SecretStr | None = Field(
        default=None, validation_alias=REPO_TOKEN_KEY_ENV
    )
    database_url: str | None = None
    data_dir: str = "./data"
    public_origin: str = "http://127.0.0.1:8000"
    cookie_secure: Literal["auto", "true", "false"] = "auto"
    trust_proxy: bool = False
    allow_remote: bool = False
    ai_max_concurrency: int = 4
    prompt_max_chars: int = 200000
    test_database_url: str | None = None

    @field_validator("cookie_secure", mode="before")
    @classmethod
    def _cookie_secure_enum(cls, value: object) -> object:
        if isinstance(value, str) and value.strip().lower() not in _COOKIE_SECURE_VALUES:
            raise ValueError("VIGIL_COOKIE_SECURE 只能是 auto、true 或 false")
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("ai_max_concurrency")
    @classmethod
    def _concurrency_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("VIGIL_AI_MAX_CONCURRENCY 必须大于 0")
        return value

    @field_validator("prompt_max_chars")
    @classmethod
    def _prompt_limit_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("VIGIL_PROMPT_MAX_CHARS 必须大于 0")
        return value

    def model_post_init(self, __context: object) -> None:
        if self.admin_password is None or not self.admin_password.get_secret_value().strip():
            raise SettingsError("VIGIL_ADMIN_PASSWORD 必须设置且不能为空白")
        if self.encryption_key is None:
            raise SettingsError(f"{ENCRYPTION_KEY_ENV} 必须设置")
        raw = self.encryption_key.get_secret_value()
        try:
            key = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SettingsError(f"{ENCRYPTION_KEY_ENV} 必须是 32 字节的 base64 编码") from exc
        if len(key) != 32:
            raise SettingsError(f"{ENCRYPTION_KEY_ENV} 必须是 32 字节的 base64 编码")
        if self.repo_token_key is None:
            raise SettingsError(f"{REPO_TOKEN_KEY_ENV} 必须设置")
        raw_repo = self.repo_token_key.get_secret_value()
        try:
            repo_key = base64.b64decode(raw_repo, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise SettingsError(
                f"{REPO_TOKEN_KEY_ENV} 必须是 32 字节的 base64 编码"
            ) from exc
        if len(repo_key) != 32:
            raise SettingsError(f"{REPO_TOKEN_KEY_ENV} 必须是 32 字节的 base64 编码")

    @property
    def admin_password_value(self) -> str:
        assert self.admin_password is not None
        return self.admin_password.get_secret_value()

    @property
    def encryption_key_bytes(self) -> bytes:
        assert self.encryption_key is not None
        return base64.b64decode(self.encryption_key.get_secret_value(), validate=True)

    @property
    def repo_token_key_bytes(self) -> bytes:
        assert self.repo_token_key is not None
        return base64.b64decode(
            self.repo_token_key.get_secret_value(), validate=True
        )

    @property
    def public_origins(self) -> tuple[str, ...]:
        return tuple(part.strip() for part in self.public_origin.split(",") if part.strip())

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        path = Path(self.data_dir).expanduser() / "vigil.db"
        return f"sqlite+aiosqlite:///{path}"

    @property
    def data_path(self) -> Path:
        return Path(self.data_dir).expanduser()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
