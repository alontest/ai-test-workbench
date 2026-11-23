"""OpenAI 兼容协议（自定义 base_url）。"""

from __future__ import annotations

import time
from typing import Any

from openai import AsyncOpenAI

from vigil_workbench.adapters.ai.base import HttpClient
from vigil_workbench.adapters.ai.base import AdapterError, ConnectionTestResult, classify_error


class OpenAICompatibleAdapter:
    def __init__(
        self,
        *,
        http_client: HttpClient | None = None,
        http_client_factory=None,  # noqa: ANN001
    ) -> None:
        self._http_client = http_client
        self._http_client_factory = http_client_factory

    def _client(self, *, base_url: str, api_key: str, timeout: float) -> AsyncOpenAI:
        client = AsyncOpenAI(
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
        params: dict[str, Any] = {
            "model": model_name,
            "messages": [{"role": "user", "content": prepared}],
        }
        if temperature is not None:
            params["temperature"] = temperature
        if max_tokens is not None:
            params["max_tokens"] = max_tokens
        try:
            response = await client.chat.completions.create(**params)
            content = response.choices[0].message.content if response.choices else None
            if not content:
                raise AdapterError("server_error", "上游返回空结果。")
            return content
        except AdapterError:
            raise
        except Exception as exc:  # SDK 异常统一映射
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
