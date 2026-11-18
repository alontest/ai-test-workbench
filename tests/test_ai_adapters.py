"""OpenAI 兼容 / Anthropic 适配器错误分类。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import json

import httpx2 as httpx
import pytest

from workbench.adapters.ai.anthropic import AnthropicAdapter
from workbench.adapters.ai.base import AdapterError, classify_error
from workbench.adapters.ai.openai_compatible import OpenAICompatibleAdapter


def _client_factory(handler):
    def make(timeout):
        return httpx.AsyncClient(
            transport=httpx.MockTransport(handler), timeout=timeout
        )

    return make


async def _openai_error(status: int) -> AdapterError:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "upstream"}})

    adapter = OpenAICompatibleAdapter(http_client_factory=_client_factory(handler))
    with pytest.raises(AdapterError) as err:
        await adapter.complete(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model_name="gpt-test",
            prepared="hi",
        )
    return err.value


@pytest.mark.asyncio
async def test_tc042_adapter_error_mapping() -> None:
    assert (await _openai_error(401)).code == "auth"
    assert (await _openai_error(403)).code == "auth"
    assert (await _openai_error(429)).code == "rate_limit"
    assert (await _openai_error(500)).code == "server_error"
    assert (await _openai_error(400)).code == "invalid_request"

    def connection_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    adapter = OpenAICompatibleAdapter(http_client_factory=_client_factory(connection_error))
    with pytest.raises(AdapterError) as err:
        await adapter.complete(
            base_url="https://api.example.com/v1",
            api_key="sk-test",
            model_name="gpt-test",
            prepared="hi",
        )
    assert err.value.code == "unreachable"

    assert classify_error(TimeoutError("slow")) == "timeout"


@pytest.mark.asyncio
async def test_tc021_connection_test_error_classification() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = OpenAICompatibleAdapter(http_client_factory=_client_factory(slow))
    result = await adapter.test_connection(
        base_url="https://api.example.com/v1",
        api_key="sk-test",
        timeout=0.05,
    )
    assert result.ok is False
    assert result.error_code == "timeout"

    def unauthorized(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "bad"}})

    adapter = OpenAICompatibleAdapter(http_client_factory=_client_factory(unauthorized))
    result = await adapter.test_connection(
        base_url="https://api.example.com/v1", api_key="sk-test", timeout=1
    )
    assert result.ok is False
    assert result.error_code == "auth"


@pytest.mark.asyncio
async def test_tc019_connection_test_timeout(settings) -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    adapter = AnthropicAdapter(http_client_factory=_client_factory(slow))
    result = await adapter.test_connection(
        base_url="https://api.anthropic.com/v1", api_key="sk-ant-test", timeout=0.05
    )
    assert result.ok is False
    assert result.error_code == "timeout"
    assert result.model_count is None


@pytest.mark.asyncio
async def test_tc019_connection_test_success_counts_models() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "data": [
                        {"id": "m1", "object": "model", "created": 0, "owned_by": "x"},
                        {"id": "m2", "object": "model", "created": 0, "owned_by": "x"},
                    ],
                },
            )
        return httpx.Response(200, json={"choices": []})

    adapter = OpenAICompatibleAdapter(http_client_factory=_client_factory(handler))
    result = await adapter.test_connection(
        base_url="https://api.example.com/v1", api_key="sk-test", timeout=1
    )
    assert result.ok is True
    assert result.model_count == 2
    assert result.error_code is None
