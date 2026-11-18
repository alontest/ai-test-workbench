"""调用编排：把会话与模型默认参数接到唯一模型出口。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from workbench.api.serialization import to_rfc3339
from workbench.db.engine import get_sessionmaker
from workbench.db.models import AiCallRecord
from workbench.services.ai_gateway import AIError, AiGateway
from workbench.services import sessions
from workbench.services.errors import DomainError

_ERROR_MESSAGES = {
    "auth": "上游鉴权失败。",
    "rate_limit": "上游限流。",
    "server_error": "上游服务异常。",
    "timeout": "上游调用超时。",
    "unreachable": "无法连接上游服务。",
    "invalid_request": "上游拒绝了请求参数。",
}


async def complete(
    session_id: int,
    *,
    prompt: str,
    temperature: float | None = None,
    max_tokens: int | None = None,
    gateway: AiGateway | None = None,
) -> dict[str, Any]:
    if temperature is not None and not 0 <= temperature <= 2:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "temperature", "message": "温度必须为 0–2"}],
        )
    if max_tokens is not None and not 1 <= max_tokens <= 1_000_000:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "maxTokens", "message": "必须为 1–1,000,000"}],
        )
    detail = await sessions.get_session(session_id)
    model = detail["model"]
    active_gateway = gateway or AiGateway()
    try:
        result = await active_gateway.complete(
            session_id,
            model["modelId"],
            prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except AIError as exc:
        message = _ERROR_MESSAGES.get(exc.code, "上游调用失败。")
        code = "ai_timeout" if exc.code == "timeout" else f"ai_{exc.code}"
        status = 504 if exc.code == "timeout" else 502
        raise DomainError(
            code,
            message,
            status_code=status,
            details=[
                {
                    "field": "callId",
                    "callId": exc.call_id,
                    "retryCount": exc.retry_count,
                    "message": message,
                }
            ],
        ) from exc

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        record = await db.get(AiCallRecord, result.call_id)
    return {
        "callId": result.call_id,
        "sessionId": session_id,
        "status": result.status,
        "resultText": result.text,
        "latencyMs": result.latency_ms,
        "retryCount": result.retry_count,
        "model": model,
        "knowledgeInjection": None,
        "createdAt": to_rfc3339(record.created_at) if record else None,
        "finishedAt": to_rfc3339(record.finished_at) if record else None,
    }
