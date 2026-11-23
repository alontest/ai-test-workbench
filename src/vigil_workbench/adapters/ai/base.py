"""适配器协议、统一错误分类与连接测试结果。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Protocol

try:
    import httpx2 as httpx
    from httpx2 import AsyncClient as HttpClient
    from httpx2 import TimeoutException as HttpTimeoutException
    from httpx2 import ConnectError as HttpConnectError
    from httpx2 import NetworkError as HttpNetworkError
except ImportError:  # pragma: no cover - SDK 旧版本回退
    import httpx  # type: ignore[no-redef]
    from httpx import AsyncClient as HttpClient
    from httpx import TimeoutException as HttpTimeoutException
    from httpx import ConnectError as HttpConnectError
    from httpx import NetworkError as HttpNetworkError


@dataclass(frozen=True)
class ConnectionTestResult:
    ok: bool
    latency_ms: int
    model_count: int | None
    error_code: str | None


class AdapterError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def classify_error(exc: BaseException) -> str:
    """把 SDK / 网络异常映射为固定错误码。"""
    if isinstance(
        exc,
        (TimeoutError, asyncio.TimeoutError, HttpTimeoutException),
    ):
        return "timeout"
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        if status in (401, 403):
            return "auth"
        if status == 429:
            return "rate_limit"
        if status >= 500:
            return "server_error"
        if 400 <= status < 500:
            return "invalid_request"
    if isinstance(exc, (HttpConnectError, HttpNetworkError)):
        return "unreachable"
    if type(exc).__name__ in {"APIConnectionError", "APITimeoutError"}:
        return "timeout" if "Timeout" in type(exc).__name__ else "unreachable"
    return "unreachable"


class ProtocolAdapter(Protocol):
    async def complete(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        prepared: str,
        temperature: float | None,
        max_tokens: int | None,
        timeout: float = 120,
    ) -> str: ...

    async def test_connection(
        self, *, base_url: str, api_key: str, timeout: float = 10
    ) -> ConnectionTestResult: ...
