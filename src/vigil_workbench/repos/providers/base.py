"""供应商适配器共用基座：引用构造、错误映射、限流头与响应体上限（ADR-206 / ADR-209）。"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from vigil_workbench.repos.constants import REPO_HTTP_TIMEOUT_SECONDS, REPO_METADATA_MAX_BYTES
from vigil_workbench.repos.types import ProviderError, RepoProviderName, RepositoryRef

_RATE_LIMIT_PHRASES = ("rate limit", "rate-limit", "ratelimit", "too many requests")


def repository_ref(source: object) -> RepositoryRef:
    """从绑定行或表单对象取出适配器所需的最小引用。"""
    provider = getattr(source, "provider", None)
    api_base_url = getattr(source, "api_base_url", None)
    if not provider or not api_base_url:
        raise ValueError("provider 与 api_base_url 不能为空。")
    repo_id = getattr(source, "repo_id", None) or getattr(source, "repo_name", None)
    repo_name = getattr(source, "repo_name", None) or repo_id
    if not repo_id or not repo_name:
        raise ValueError("repo_id 与 repo_name 不能同时为空。")
    return RepositoryRef(
        provider=provider,
        repo_id=str(repo_id),
        repo_name=str(repo_name),
        api_base_url=api_base_url,
        org_id=getattr(source, "org_id", None),
        owner=getattr(source, "owner", None),
        default_branch=getattr(source, "default_branch", None),
    )


class FileTooLarge(Exception):
    """文件超过客户端上限；服务层据此映射 ``413 repo_file_too_large``。

    ``encoding`` 是供应商侧的原始编码，用于审计记录（``text`` / ``base64``）。
    """

    def __init__(
        self, size_bytes: int, limit_bytes: int, *, encoding: str = "base64"
    ) -> None:
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        self.encoding = encoding
        super().__init__(f"文件大小 {size_bytes} 字节，超过上限 {limit_bytes} 字节。")


def header_value(headers: Mapping[str, str], name: str) -> str | None:
    """大小写不敏感地读响应头。"""
    value = headers.get(name)
    if value is not None:
        return value
    lowered = name.lower()
    for key, candidate in headers.items():
        if key.lower() == lowered:
            return candidate
    return None


def has_rate_limit_signal(headers: Mapping[str, str], body_text: str) -> bool:
    if (header_value(headers, "retry-after") or "").strip():
        return True
    if (header_value(headers, "x-ratelimit-remaining") or "").strip() == "0":
        return True
    lowered = body_text.lower()
    return any(phrase in lowered for phrase in _RATE_LIMIT_PHRASES)


def retry_after_at(
    headers: Mapping[str, str], *, now: datetime | None = None
) -> datetime | None:
    """``retry-after``（秒）优先，其次 ``x-ratelimit-reset``（epoch 秒）；非法即 ``None``。"""
    current = now or datetime.now(timezone.utc)
    retry_after = (header_value(headers, "retry-after") or "").strip()
    if retry_after.isdigit():
        return current + timedelta(seconds=int(retry_after))
    reset = (header_value(headers, "x-ratelimit-reset") or "").strip()
    if reset.isdigit():
        return datetime.fromtimestamp(int(reset), tz=timezone.utc)
    return None


def map_httpx_exception(exc: BaseException) -> ProviderError:
    if isinstance(exc, httpx.TimeoutException):
        return ProviderError("timeout")
    return ProviderError("network")


def classify_response(
    status_code: int,
    headers: Mapping[str, str],
    body: bytes,
    *,
    now: datetime | None = None,
) -> ProviderError | None:
    """按 api-spec §2 的 11 行映射表判定；2xx 且无限流信号返回 ``None``。"""
    body_text = body.decode("utf-8", errors="ignore")

    if status_code == 429:
        return ProviderError(
            "rate_limited",
            status_code=status_code,
            retry_after_at=retry_after_at(headers, now=now),
        )
    if status_code == 401:
        return ProviderError("auth", status_code=status_code)
    if status_code == 403:
        if has_rate_limit_signal(headers, body_text):
            return ProviderError(
                "rate_limited",
                status_code=status_code,
                retry_after_at=retry_after_at(headers, now=now),
            )
        return ProviderError("permission_denied", status_code=status_code)
    if status_code == 404:
        return ProviderError("not_found", status_code=status_code)
    if 500 <= status_code < 600:
        return ProviderError("server_error", status_code=status_code)
    if 200 <= status_code < 300:
        if (header_value(headers, "x-ratelimit-remaining") or "").strip() == "0":
            return ProviderError(
                "rate_limited",
                status_code=status_code,
                retry_after_at=retry_after_at(headers, now=now),
            )
        return None
    return ProviderError("invalid_response", status_code=status_code)


class BaseProvider:
    """所有供应商共用同一 HTTP 客户端策略：不跟随重定向、不自动重试、只发 GET。"""

    name: RepoProviderName

    def __init__(
        self,
        ref: RepositoryRef,
        token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = REPO_HTTP_TIMEOUT_SECONDS,
    ) -> None:
        if not token or not token.strip():
            raise ValueError("供应商令牌不能为空。")
        self._ref = ref
        self.token_expires_at: datetime | None = None
        self._client = httpx.AsyncClient(
            base_url=ref.api_base_url.rstrip("/"),
            headers=self._auth_headers(token),
            timeout=httpx.Timeout(timeout),
            follow_redirects=False,
            transport=transport
            if transport is not None
            else httpx.AsyncHTTPTransport(retries=0),
        )

    def _auth_headers(self, token: str) -> dict[str, str]:
        raise NotImplementedError

    def _capture_token_expiry(self, headers: Mapping[str, str]) -> None:
        """基类不读过期头；GitHub 覆盖。"""

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _read_body(self, response: httpx.Response) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > REPO_METADATA_MAX_BYTES:
                raise ProviderError(
                    "invalid_response", status_code=response.status_code
                )
            chunks.append(chunk)
        return b"".join(chunks)

    async def _get_json(
        self, path: str, *, params: dict[str, Any] | None = None
    ) -> tuple[Any, httpx.Response]:
        try:
            async with self._client.stream("GET", path, params=params) as response:
                self._capture_token_expiry(response.headers)
                body = await self._read_body(response)
                if not response.is_success:
                    error = classify_response(
                        response.status_code, response.headers, body
                    )
                    raise error or ProviderError(
                        "invalid_response", status_code=response.status_code
                    )
                try:
                    payload = json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    raise ProviderError(
                        "invalid_response", status_code=response.status_code
                    ) from None
                limited = classify_response(
                    response.status_code, response.headers, b""
                )
                if limited is not None:
                    raise limited
                return payload, response
        except httpx.HTTPError as exc:
            raise map_httpx_exception(exc) from None


__all__ = [
    "BaseProvider",
    "FileTooLarge",
    "classify_response",
    "has_rate_limit_signal",
    "header_value",
    "map_httpx_exception",
    "repository_ref",
    "retry_after_at",
]
