"""Anthropic 官方 Messages API。"""

from __future__ import annotations

import time

from anthropic import AsyncAnthropic

from workbench.adapters.ai.base import HttpClient
from workbench.adapters.ai.base import AdapterError, ConnectionTestResult, classify_error

_DEFAULT_MAX_TOKENS = 1024


class AnthropicAdapter:
    def __init__(
        self,
        *,
        http_client: HttpClient | None = None,
        http_client_factory=None,  # noqa: ANN001
    ) -> None:
        self._http_client = http_client
        self._http_client_factory = http_client_factory

    def _client(self, *, base_url: str, api_key: str, timeout: float) -> AsyncAnthropic:
        client = AsyncAnthropic(
            base_url=base_url,
            api_key=api_key,
            max_retries=0,
            timeout=timeout,
            http_client=(
                self._http_client_factory(timeout)
                if self._http_client_factory is not None
                else self._http_client
            ),
        )
        return client

    async def complete(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str,
        prepared: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float = 120,
    ) -> str:
        client = self._client(base_url=base_url, api_key=api_key, timeout=timeout)
        params: dict[str, object] = {
            "model": model_name,
            "max_tokens": max_tokens or _DEFAULT_MAX_TOKENS,
            "messages": [{"role": "user", "content": prepared}],
        }
        if temperature is not None:
            params["temperature"] = temperature
        try:
            response = await client.messages.create(**params)
            text = "".join(
                getattr(block, "text", "") for block in response.content if getattr(block, "type", "") == "text"
            )
            if not text:
                raise AdapterError("server_error", "上游返回空结果。")
            return text
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError(classify_error(exc), "上游调用失败。") from exc

    async def test_connection(
        self, *, base_url: str, api_key: str, timeout: float = 10
    ) -> ConnectionTestResult:
        started = time.perf_counter()
        client = self._client(base_url=base_url, api_key=api_key, timeout=timeout)
        try:
            models = await client.models.list()
            return ConnectionTestResult(
                ok=True,
                latency_ms=int((time.perf_counter() - started) * 1000),
                model_count=len(models.data),
                error_code=None,
            )
        except Exception as exc:
            return ConnectionTestResult(
                ok=False,
                latency_ms=int((time.perf_counter() - started) * 1000),
                model_count=None,
                error_code=classify_error(exc),
            )
