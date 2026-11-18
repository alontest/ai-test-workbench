"""会话与事件：ADR-041 冻结签名 create / append_event。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from workbench.core.entrances import ENTRANCE_KEYS
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.repositories import events as events_repo
from workbench.db.repositories import sessions as sessions_repo
from workbench.db.models import AnalysisSession, ModelBinding, ProjectContext, ProviderConfig, SessionEvent
from workbench.services.errors import DomainError

EntranceKey = Literal[
    "case-library",
    "bug-analysis",
    "log-triage",
    "sql-analysis",
    "regression-list",
    "test-report",
]
EventType = Literal["input_text", "artifact", "call", "status_change", "knowledge_injection"]
SessionStatus = Literal["in_progress", "completed", "failed"]

EVENT_REQUIRED_KEYS: dict[str, tuple[str, ...]] = {
    "input_text": ("title", "text", "charCount"),
    "artifact": ("artifactId", "fileName", "byteSize", "mimeType", "kind"),
    "call": (
        "callId",
        "modelId",
        "modelDisplayName",
        "status",
        "latencyMs",
        "retryCount",
        "promptPreview",
        "errorCode",
    ),
    "status_change": ("from", "to", "actor", "at"),
    "knowledge_injection": (
        "items",
        "promptChars",
        "injectedChars",
        "totalChars",
    ),
}


class SessionView(TypedDict):
    session_id: int
    project_id: int
    entrance_key: EntranceKey
    title: str
    status: SessionStatus
    model_id: int
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class EventView(TypedDict):
    event_id: int
    session_id: int
    type: EventType
    payload: dict[str, Any]
    created_at: datetime


def session_to_view(row: AnalysisSession) -> SessionView:
    return {
        "session_id": row.session_id,
        "project_id": row.project_id,
        "entrance_key": row.entrance_key,  # type: ignore[typeddict-item]
        "title": row.title,
        "status": row.status,  # type: ignore[typeddict-item]
        "model_id": row.model_id,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "closed_at": row.closed_at,
    }


def event_to_view(row: SessionEvent) -> EventView:
    return {
        "event_id": row.event_id,
        "session_id": row.session_id,
        "type": row.type,  # type: ignore[typeddict-item]
        "payload": dict(row.payload or {}),
        "created_at": row.created_at,
    }


def _validate_title(title: str) -> str:
    cleaned = title.strip()
    if not 1 <= len(cleaned) <= 200:
        raise DomainError(
            "validation_error",
            "会话标题长度必须为 1–200 个字符。",
            details=[{"field": "title", "message": "长度必须为 1–200"}],
        )
    return cleaned


def validate_event_payload(event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    required = EVENT_REQUIRED_KEYS.get(event_type)
    if required is None:
        raise DomainError(
            "validation_error",
            "未知的事件类型。",
            details=[{"field": "eventType", "message": f"unknown event type {event_type}"}],
        )
    missing = [key for key in required if key not in payload]
    if missing:
        raise DomainError(
            "validation_error",
            "事件缺少必需字段。",
            details=[{"field": "payload", "message": f"missing {', '.join(missing)}"}],
        )
    return dict(payload)


async def create(
    *,
    project_id: int,
    entrance_key: EntranceKey,
    title: str,
    model_id: int,
) -> SessionView:
    cleaned_title = _validate_title(title)
    if entrance_key not in ENTRANCE_KEYS:
        raise DomainError(
            "validation_error",
            "入口不存在。",
            details=[{"field": "entranceKey", "message": "unknown entrance"}],
        )

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        project = await db.get(ProjectContext, project_id)
        if project is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "project not found"}],
            )
        model = await db.get(ModelBinding, model_id)
        if model is None:
            raise DomainError(
                "model_not_found",
                "模型不存在。",
                status_code=404,
                details=[{"field": "modelId", "message": "model not found"}],
            )
        if not model.enabled:
            raise DomainError(
                "model_disabled",
                "模型已停用。",
                status_code=409,
                details=[{"field": "modelId", "message": "model disabled"}],
            )
        provider = await db.get(ProviderConfig, model.provider_id)
        if provider is None or not provider.enabled:
            raise DomainError(
                "provider_disabled",
                "提供商已停用。",
                status_code=409,
                details=[{"field": "modelId", "message": "provider disabled"}],
            )

        now = utcnow()
        row = AnalysisSession(
            project_id=project_id,
            entrance_key=entrance_key,
            title=cleaned_title,
            status="in_progress",
            model_id=model_id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return session_to_view(row)


async def append_event(
    session_id: int,
    event_type: EventType,
    payload: Mapping[str, Any],
    *,
    actor: str = "local-user",
) -> EventView:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        session = await sessions_repo.get(db, session_id)
        if session is None:
            raise DomainError("session_not_found", "会话不存在。", status_code=404)
        if session.status != "in_progress":
            raise DomainError(
                "session_closed",
                "会话已结束，不能继续写入。",
                status_code=409,
                details=[{"field": "sessionId", "message": f"session {session_id} is {session.status}"}],
            )
        row = await append_event_in_db(db, session, event_type, payload, actor=actor)
        await db.commit()
        await db.refresh(row)
        return event_to_view(row)


async def append_event_in_db(
    db: AsyncSession,
    session: AnalysisSession,
    event_type: str,
    payload: Mapping[str, Any],
    *,
    actor: str = "local-user",
) -> SessionEvent:
    """在同一事务内写事件并刷新会话。调用方负责 commit。"""
    stored = validate_event_payload(event_type, payload)
    now = utcnow()
    row = SessionEvent(
        session_id=session.session_id,
        type=event_type,
        payload=stored,
        created_at=now,
    )
    db.add(row)
    session.updated_at = _next_timestamp(session.updated_at, now)
    await db.flush()
    return row


def _next_timestamp(previous: datetime | None, now: datetime) -> datetime:
    if previous is not None and now <= previous:
        return previous.replace(microsecond=min(previous.microsecond + 1, 999999))
    return now


async def _get_session(db: AsyncSession, session_id: int) -> AnalysisSession:
    row = await db.get(AnalysisSession, session_id)
    if row is None:
        raise DomainError("session_not_found", "会话不存在。", status_code=404)
    return row


async def list_events(db: AsyncSession, session_id: int) -> list[SessionEvent]:
    return await events_repo.list_for_session(db, session_id)
