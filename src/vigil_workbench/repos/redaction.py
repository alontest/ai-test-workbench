"""日志与异常脱敏出口（ADR-215）。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from vigil_workbench.repos.types import ProviderError

SAFE_LOG_FIELDS = ("bindingId", "provider", "repoKey", "statusCode", "category")


def safe_log_fields(values: Mapping[str, Any]) -> dict[str, Any]:
    """白名单过滤；未知键（含令牌、密文、响应正文）一律丢弃。"""
    return {
        key: values[key]
        for key in SAFE_LOG_FIELDS
        if key in values and values[key] is not None
    }


def redact_provider_exception(
    error: ProviderError,
    *,
    provider: str | None = None,
    binding_id: str | None = None,
    repo_key: str | None = None,
) -> dict[str, Any]:
    """只保留分类与状态码；不含异常文案。"""
    fields: dict[str, Any] = {
        "provider": provider,
        "bindingId": binding_id,
        "repoKey": repo_key,
        "statusCode": error.status_code,
        "category": error.category,
    }
    return safe_log_fields(fields)


__all__ = ["SAFE_LOG_FIELDS", "redact_provider_exception", "safe_log_fields"]
