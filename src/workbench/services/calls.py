"""调用编排：把会话与模型默认参数接到唯一模型出口。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from workbench.api.pagination import encode_cursor
from workbench.api.serialization import to_rfc3339
from workbench.core.ports import (
    InvalidCodeRef,
    KnowledgeRef,
    get_injection_preparer,
)
from workbench.core.redaction import redact
from workbench.db.engine import get_sessionmaker
from workbench.db.models import AiCallRecord, ProjectContext
from workbench.db.repositories import calls as calls_repo
from workbench.services.ai_gateway import AIError, AiGateway
from workbench.services import sessions
from workbench.services.errors import DomainError
from workbench.services.injection_snapshot import existing_kb_id_set, with_kb_deleted

_CALL_STATUSES = {"success", "failed", "timeout"}

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
    knowledge_refs: Sequence[Any] | None = None,
    confirm_invalid_codes: Sequence[Any] | None = None,
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
    prepared = prompt
    injection = None
    refs = tuple(_as_knowledge_ref(item) for item in (knowledge_refs or ()))
    confirms = tuple(_as_invalid_code(item) for item in (confirm_invalid_codes or ()))
    if refs:
        preparer = get_injection_preparer()
        if preparer is None:
            raise DomainError(
                "knowledge_unavailable",
                "本部署未安装知识库服务。",
                status_code=409,
            )
        prepared_injection = await preparer.prepare_for_call(
            session_id=session_id,
            project_id=detail["project"]["projectId"],
            prompt=prompt,
            knowledge_refs=refs,
            confirm_invalid_codes=confirms,
        )
        prepared = prepared_injection.prepared
        injection = prepared_injection.snapshot
    active_gateway = gateway or AiGateway()
    try:
        result = await active_gateway.complete(
            session_id,
            model["modelId"],
            prepared,
            temperature=temperature,
            max_tokens=max_tokens,
            injection=injection,
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
        present = await existing_kb_id_set(db)
    raw_injection = record.knowledge_injection if record else None
    if isinstance(raw_injection, dict):
        raw_injection = raw_injection.get("items")
    knowledge_injection = with_kb_deleted(raw_injection, present)
    return {
        "callId": result.call_id,
        "sessionId": session_id,
        "status": result.status,
        "resultText": result.text,
        "latencyMs": result.latency_ms,
        "retryCount": result.retry_count,
        "model": model,
        "knowledgeInjection": knowledge_injection,
        "createdAt": to_rfc3339(record.created_at) if record else None,
        "finishedAt": to_rfc3339(record.finished_at) if record else None,
    }


def _as_knowledge_ref(item: Any) -> KnowledgeRef:
    if isinstance(item, KnowledgeRef):
        return item
    if isinstance(item, dict):
        kb_id = item.get("kbId", item.get("kb_id"))
        codes = item.get("entryCodes", item.get("entry_codes", ()))
    else:
        kb_id = item.kb_id
        codes = item.entry_codes
    return KnowledgeRef(kb_id=str(kb_id), entry_codes=tuple(codes or ()))


def _as_invalid_code(item: Any) -> InvalidCodeRef:
    if isinstance(item, InvalidCodeRef):
        return item
    if isinstance(item, dict):
        kb_id = item.get("kbId", item.get("kb_id"))
        code = item.get("code")
    else:
        kb_id = item.kb_id
        code = item.code
    return InvalidCodeRef(kb_id=str(kb_id), code=str(code))


def _parse_rfc3339(value: str, field: str) -> datetime:
    try:
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        moment = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": field, "message": "时间格式必须为 RFC 3339"}],
        ) from exc
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc).replace(tzinfo=None)
    return moment


def _parse_call_cursor(cursor: dict[str, Any] | None) -> tuple[datetime, int] | None:
    if cursor is None:
        return None
    raw_time = cursor.get("created_at")
    raw_id = cursor.get("call_id")
    if not isinstance(raw_time, str) or not isinstance(raw_id, int):
        raise DomainError("validation_error", "游标非法。")
    return (_parse_rfc3339(raw_time, "cursor"), raw_id)


def _call_to_api(
    record: AiCallRecord,
    project: ProjectContext,
    *,
    include_result: bool,
    kb_present: set[str] | None,
) -> dict[str, Any]:
    preview = redact(record.prompt_preview or "", max_length=200)
    error_message = (
        redact(record.error_message, max_length=1000) if record.error_message else None
    )
    raw_injection = record.knowledge_injection
    if isinstance(raw_injection, dict):
        raw_injection = raw_injection.get("items")
    item: dict[str, Any] = {
        "callId": record.call_id,
        "sessionId": record.session_id,
        "project": {"projectId": project.project_id, "name": project.name},
        "model": {
            "modelId": record.model_id,
            "displayName": record.display_name_snapshot,
            "providerName": record.provider_name_snapshot,
        },
        "status": record.status,
        "promptPreview": preview,
        "promptCharCount": record.prompt_char_count,
        "knowledgeInjection": with_kb_deleted(raw_injection, kb_present),
        "latencyMs": record.latency_ms,
        "retryCount": record.retry_count,
        "errorCode": record.error_code,
        "errorMessage": error_message,
        "createdAt": to_rfc3339(record.created_at),
        "finishedAt": to_rfc3339(record.finished_at),
    }
    if include_result:
        item["resultText"] = record.result_text
    return item


async def list_calls(
    *,
    session_id: int | None = None,
    project_id: int | None = None,
    status: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    limit: int = 20,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    if status is not None and status not in _CALL_STATUSES:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "status", "message": "非法调用状态"}],
        )
    start = _parse_rfc3339(created_from, "from") if created_from else None
    end = _parse_rfc3339(created_to, "to") if created_to else None
    if start is not None and end is not None and start > end:
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "from", "message": "from 不能晚于 to"}],
        )
    after = _parse_call_cursor(cursor)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        rows = await calls_repo.list_with_project(
            db,
            session_id=session_id,
            project_id=project_id,
            status=status,
            created_from=start,
            created_to=end,
            after=after,
            limit=limit + 1,
        )
        present = await existing_kb_id_set(db)
    has_more = len(rows) > limit
    page = rows[:limit]
    items = [
        _call_to_api(record, project, include_result=False, kb_present=present)
        for record, project in page
    ]
    next_cursor = None
    if has_more and page:
        last, _project = page[-1]
        next_cursor = encode_cursor(
            {"created_at": last.created_at.isoformat(), "call_id": last.call_id}
        )
    return items, next_cursor


async def get_call(call_id: int) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await calls_repo.get_with_project(db, call_id)
        present = await existing_kb_id_set(db)
    if row is None:
        raise DomainError("call_not_found", "调用记录不存在。", status_code=404)
    record, project = row
    return _call_to_api(record, project, include_result=True, kb_present=present)
