"""唯一模型出口：ADR-041 冻结签名 AiGateway.complete。"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from workbench.adapters.ai.base import AdapterError, ProtocolAdapter
from workbench.adapters.ai.anthropic import AnthropicAdapter
from workbench.adapters.ai.openai_compatible import OpenAICompatibleAdapter
from workbench.config import get_settings
from workbench.core.constants import AI_ATTEMPT_TIMEOUT_SECONDS
from workbench.core.crypto import CredentialUnavailable, decrypt
from workbench.core.redaction import redact
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.models import AiCallRecord, AnalysisSession, ModelBinding, ProviderConfig
from workbench.services.errors import DomainError
from workbench.services.sessions import append_event_in_db

_RETRYABLE_CODES = {"server_error", "unreachable"}


@dataclass(frozen=True)
class InjectionItem:
    kb_id: int
    kb_name: str
    kb_version: int
    entry_codes: tuple[str, ...]
    injected_chars: int


@dataclass(frozen=True)
class InjectionSnapshot:
    items: tuple[InjectionItem, ...]
    prompt_chars: int
    injected_chars: int
    total_chars: int
    excluded_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class AIResult:
    call_id: int
    text: str
    status: Literal["success"]
    latency_ms: int
    retry_count: int
    model_id: int
    model_display_name: str
    knowledge_injection: tuple[InjectionItem, ...] | None = None


class AIError(Exception):
    def __init__(self, code: str, message: str, call_id: int, retry_count: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.call_id = call_id
        self.retry_count = retry_count


def _default_adapter(protocol: str) -> ProtocolAdapter:
    if protocol == "anthropic":
        return AnthropicAdapter()
    return OpenAICompatibleAdapter()


class AiGateway:
    def __init__(
        self,
        *,
        adapter: ProtocolAdapter | None = None,
        adapter_factory=None,  # noqa: ANN001
        attempt_timeout: float | None = None,
        retry_backoff: float = 2.0,
    ) -> None:
        self._adapter = adapter
        self._adapter_factory = adapter_factory or _default_adapter
        self._attempt_timeout = (
            AI_ATTEMPT_TIMEOUT_SECONDS if attempt_timeout is None else attempt_timeout
        )
        self._retry_backoff = retry_backoff
        self._semaphore: asyncio.Semaphore | None = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(get_settings().ai_max_concurrency)
        return self._semaphore

    async def complete(
        self,
        session_id: int,
        model_id: int,
        prepared: str,
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        injection: InjectionSnapshot | None = None,
    ) -> AIResult:
        settings = get_settings()
        if not prepared or len(prepared) > settings.prompt_max_chars:
            raise DomainError(
                "prompt_too_long",
                "提示超过字符上限。",
                details=[
                    {"field": "prompt", "charCount": len(prepared), "maxChars": settings.prompt_max_chars}
                ],
            )
        if injection is not None:
            _validate_injection(injection, prepared)

        context = await self._load_context(session_id, model_id)
        adapter = self._adapter or self._adapter_factory(context["protocol"])

        async with self._get_semaphore():
            record_id = await self._insert_running(context, prepared, injection)
            started = time.perf_counter()
            retry_count = 0
            status = "failed"
            error_code: str | None = None
            text = ""
            try:
                for attempt in range(2):
                    try:
                        async with asyncio.timeout(self._attempt_timeout):
                            text = await adapter.complete(
                                base_url=context["base_url"],
                                api_key=context["api_key"],
                                model_name=context["model_name"],
                                prepared=prepared,
                                temperature=(
                                    context["default_temperature"]
                                    if temperature is None
                                    else temperature
                                ),
                                max_tokens=(
                                    context["default_max_tokens"] if max_tokens is None else max_tokens
                                ),
                                timeout=self._attempt_timeout,
                            )
                        status = "success"
                        error_code = None
                        break
                    except TimeoutError:
                        status = "timeout"
                        error_code = "timeout"
                        break
                    except AdapterError as exc:
                        error_code = exc.code
                        if exc.code in _RETRYABLE_CODES and attempt == 0:
                            retry_count = 1
                            if self._retry_backoff:
                                await asyncio.sleep(self._retry_backoff)
                            continue
                        status = "failed"
                        break
            except asyncio.CancelledError:
                latency_ms = int((time.perf_counter() - started) * 1000)
                await self._finalize(
                    record_id,
                    session_id,
                    context,
                    status="failed",
                    error_code="interrupted",
                    error_message="call cancelled",
                    text=None,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                )
                raise

            latency_ms = int((time.perf_counter() - started) * 1000)
            if status == "success":
                await self._finalize(
                    record_id,
                    session_id,
                    context,
                    status="success",
                    error_code=None,
                    error_message=None,
                    text=text,
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                )
                return AIResult(
                    call_id=record_id,
                    text=text,
                    status="success",
                    latency_ms=latency_ms,
                    retry_count=retry_count,
                    model_id=model_id,
                    model_display_name=context["display_name"],
                    knowledge_injection=injection.items if injection is not None else None,
                )

            assert error_code is not None
            await self._finalize(
                record_id,
                session_id,
                context,
                status="timeout" if status == "timeout" else "failed",
                error_code=error_code,
                error_message=_error_message(error_code),
                text=None,
                latency_ms=latency_ms,
                retry_count=retry_count,
            )
            raise AIError(error_code, _error_message(error_code), record_id, retry_count)

    async def _load_context(self, session_id: int, model_id: int) -> dict:
        settings = get_settings()
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            session = await db.get(AnalysisSession, session_id)
            if session is None:
                raise DomainError("session_not_found", "会话不存在。", status_code=404)
            if session.status != "in_progress":
                raise DomainError(
                    "session_closed",
                    "会话已结束，不能继续写入。",
                    status_code=409,
                    details=[{"field": "sessionId", "message": f"session {session_id} is {session.status}"}],
                )
            model = await db.get(ModelBinding, model_id)
            if model is None:
                raise DomainError("model_not_found", "模型不存在。", status_code=404)
            if not model.enabled:
                raise DomainError("model_disabled", "模型已停用。", status_code=409)
            provider = await db.get(ProviderConfig, model.provider_id)
            if provider is None or not provider.enabled:
                raise DomainError("provider_disabled", "提供商已停用。", status_code=409)
            try:
                api_key = decrypt(
                    provider.api_key_ciphertext, key=settings.encryption_key_bytes
                )
            except CredentialUnavailable as exc:
                raise DomainError(
                    "provider_credential_unavailable",
                    "提供商凭据不可用。",
                    status_code=502,
                ) from exc
            return {
                "session": session,
                "model": model,
                "provider": provider,
                "protocol": provider.protocol,
                "base_url": provider.base_url,
                "api_key": api_key,
                "model_name": model.model_name,
                "display_name": model.display_name,
                "provider_name": provider.name,
                "default_temperature": float(model.default_temperature),
                "default_max_tokens": model.default_max_tokens,
            }

    async def _insert_running(
        self,
        context: dict,
        prepared: str,
        injection: InjectionSnapshot | None,
    ) -> int:
        sessionmaker = get_sessionmaker()
        now = utcnow()
        async with sessionmaker() as db:
            session = await db.get(AnalysisSession, context["session"].session_id)
            assert session is not None
            injection_payload = _injection_payload(injection)
            row = AiCallRecord(
                session_id=session.session_id,
                model_id=context["model"].model_id,
                provider_id=context["provider"].provider_id,
                model_name_snapshot=context["model_name"],
                display_name_snapshot=context["display_name"],
                provider_name_snapshot=context["provider_name"],
                protocol_snapshot=context["protocol"],
                status="running",
                prompt_digest=hashlib.sha256(prepared.encode("utf-8")).hexdigest(),
                prompt_preview=redact(prepared, max_length=200),
                prompt_char_count=len(prepared),
                knowledge_injection=injection_payload,
                injected_chars=injection.injected_chars if injection else 0,
                prompt_chars=injection.prompt_chars if injection else len(prepared),
                total_chars=injection.total_chars if injection else len(prepared),
                created_at=now,
            )
            db.add(row)
            await db.flush()
            if injection_payload is not None:
                await append_event_in_db(
                    db, session, "knowledge_injection", injection_payload
                )
            await db.commit()
            return row.call_id

    async def _finalize(
        self,
        record_id: int,
        session_id: int,
        context: dict,
        *,
        status: str,
        error_code: str | None,
        error_message: str | None,
        text: str | None,
        latency_ms: int,
        retry_count: int,
    ) -> None:
        sessionmaker = get_sessionmaker()
        async with sessionmaker() as db:
            record = await db.get(AiCallRecord, record_id)
            if record is None:  # pragma: no cover - 记录应始终存在
                return
            record.status = status
            record.error_code = error_code
            record.error_message = error_message
            record.result_text = text
            record.latency_ms = latency_ms
            record.retry_count = retry_count
            record.finished_at = utcnow()
            session = await db.get(AnalysisSession, session_id)
            if session is not None:
                await append_event_in_db(
                    db,
                    session,
                    "call",
                    {
                        "callId": record_id,
                        "modelId": context["model"].model_id,
                        "modelDisplayName": context["display_name"],
                        "status": status,
                        "latencyMs": latency_ms,
                        "retryCount": retry_count,
                        "promptPreview": record.prompt_preview,
                        "errorCode": error_code,
                    },
                    actor="system" if error_code == "interrupted" else "local-user",
                )
            await db.commit()


def _injection_payload(injection: InjectionSnapshot | None) -> dict | None:
    if injection is None:
        return None
    return {
        "items": [
            {
                "kbId": item.kb_id,
                "kbName": item.kb_name,
                "kbVersion": item.kb_version,
                "entryCodes": list(item.entry_codes),
                "injectedChars": item.injected_chars,
            }
            for item in injection.items
        ],
        "promptChars": injection.prompt_chars,
        "injectedChars": injection.injected_chars,
        "totalChars": injection.total_chars,
        "excludedCodes": list(injection.excluded_codes),
    }


def _validate_injection(injection: InjectionSnapshot, prepared: str) -> None:
    injected = sum(item.injected_chars for item in injection.items)
    valid = (
        injection.injected_chars == injected
        and injection.total_chars == injection.prompt_chars + injected
        and injection.total_chars == len(prepared)
    )
    if not valid:
        raise DomainError(
            "injection_snapshot_mismatch",
            "注入快照与提示正文不一致。",
            details=[{"field": "injection", "message": "character counts mismatch"}],
        )


def _error_message(code: str) -> str:
    return {
        "auth": "上游鉴权失败。",
        "rate_limit": "上游限流。",
        "server_error": "上游服务异常。",
        "timeout": "上游调用超时。",
        "unreachable": "无法连接上游服务。",
        "invalid_request": "上游拒绝了请求参数。",
        "interrupted": "调用被中断。",
    }.get(code, "上游调用失败。")
