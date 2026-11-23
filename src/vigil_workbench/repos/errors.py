"""仓库集成领域错误族。

只带错误码、状态与固定文案；不携带令牌、密文、请求头或供应商响应原文
（ADR-215）。继承 ``DomainError`` 以便 API 层沿用统一错误体。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone

from vigil_workbench.services.errors import DomainError

from vigil_workbench.repos.types import ProviderError

PROVIDER_ERROR_MAP: Mapping[str, tuple[int, str, str]] = {
    "auth": (502, "provider_auth_failed", "供应商令牌无效或已过期。"),
    "permission_denied": (502, "provider_permission_denied", "供应商拒绝访问或资源不存在。"),
    "not_found": (502, "provider_permission_denied", "供应商拒绝访问或资源不存在。"),
    "rate_limited": (502, "provider_rate_limited", "供应商限流，请稍后重试。"),
    "network": (502, "provider_unreachable", "无法连接供应商服务。"),
    "timeout": (502, "provider_timeout", "供应商请求超时。"),
    "server_error": (502, "provider_unreachable", "供应商服务异常。"),
    "invalid_response": (502, "provider_invalid_response", "供应商响应无法解析。"),
}


def isoformat_utc(value: datetime) -> str:
    """UTC naive → RFC 3339；其他时区先换算到 UTC。"""
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


class RepoDomainError(DomainError):
    """仓库域错误基类。"""


class RepoValidationError(RepoDomainError):
    """外部输入非法；``code`` 取 api-spec 的固定码。"""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: Sequence[Mapping[str, object]] | Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(code, message, status_code=400, details=details)


class RepoConcurrencyError(RepoDomainError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message, status_code=409)


FILE_TOO_LARGE_MESSAGE = "文件大小超过上限。"
FILE_BINARY_MESSAGE = "文件为二进制，无法以文本展示。"
FILE_NOT_UTF8_MESSAGE = "文件不是合法的 UTF-8 文本。"


def file_too_large(size_bytes: int, limit_bytes: int) -> RepoDomainError:
    """413：只报实际大小与上限，不截断、不返回正文。"""
    return RepoDomainError(
        "repo_file_too_large",
        FILE_TOO_LARGE_MESSAGE,
        status_code=413,
        details=[
            {
                "field": "sizeBytes",
                "message": f"实际 {size_bytes} 字节，上限 {limit_bytes} 字节。",
            }
        ],
    )


def file_binary() -> RepoDomainError:
    return RepoDomainError(
        "repo_file_binary", FILE_BINARY_MESSAGE, status_code=415
    )


def file_not_utf8() -> RepoDomainError:
    return RepoDomainError(
        "repo_file_not_utf8", FILE_NOT_UTF8_MESSAGE, status_code=422
    )


class RepoProviderError(RepoDomainError):
    """把 ``ProviderError`` 映射为固定 HTTP 码；details 只含可公开的分类字段。"""

    def __init__(
        self,
        error: ProviderError,
        *,
        provider: str | None = None,
        binding_id: str | None = None,
    ) -> None:
        status_code, code, message = PROVIDER_ERROR_MAP[error.category]
        detail: dict[str, object] = {"category": error.category}
        if provider is not None:
            detail["provider"] = provider
        if error.status_code is not None:
            detail["statusCode"] = error.status_code
        if error.retry_after_at is not None:
            detail["retryAfterAt"] = isoformat_utc(error.retry_after_at)
        if binding_id is not None:
            detail["bindingId"] = binding_id
        super().__init__(code, message, status_code=status_code, details=[detail])
        self.category = error.category
        self.retry_after_at = error.retry_after_at


__all__ = [
    "FILE_BINARY_MESSAGE",
    "FILE_NOT_UTF8_MESSAGE",
    "FILE_TOO_LARGE_MESSAGE",
    "PROVIDER_ERROR_MAP",
    "RepoConcurrencyError",
    "RepoDomainError",
    "RepoProviderError",
    "RepoValidationError",
    "file_binary",
    "file_not_utf8",
    "file_too_large",
    "isoformat_utc",
]
