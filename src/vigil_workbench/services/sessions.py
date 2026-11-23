"""会话与事件：ADR-041 冻结签名 create / append_event。"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.core.entrances import ENTRANCE_KEYS
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.repositories import events as events_repo
from vigil_workbench.db.repositories import sessions as sessions_repo
from vigil_workbench.db.models import AnalysisSession, ModelBinding, ProjectContext, ProviderConfig, SessionEvent
from vigil_workbench.services.errors import DomainError
from vigil_workbench.services.injection_snapshot import existing_kb_id_set, with_kb_deleted

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


# ---------------------------------------------------------------------------
# 批次 B：会话状态流转、列表、时间线分页与删除
# ---------------------------------------------------------------------------

import logging
from datetime import datetime

from sqlalchemy import delete, select

from vigil_workbench.adapters.fs import storage
from vigil_workbench.api.pagination import encode_cursor
from vigil_workbench.core.constants import PROMPT_MAX_CHARS
from vigil_workbench.core.validation import require_text
from vigil_workbench.db.models import AiCallRecord, Artifact

logger = logging.getLogger(__name__)


def _iso(value: datetime) -> str:
    return value.isoformat() + "Z"


def _closed_error(session_id: int, status: str) -> DomainError:
    return DomainError(
        "session_closed",
        "会话已结束，不能继续写入。",
        status_code=409,
        details=[{"field": "sessionId", "message": f"session {session_id} is {status}"}],
    )


async def complete_session(session_id: int) -> SessionView:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        session = await _get_session(db, session_id)
        if session.status != "in_progress":
            raise _closed_error(session_id, session.status)
        now = utcnow()
        previous = session.status
        session.status = "completed"
        session.closed_at = now
        await append_event_in_db(
            db,
            session,
            "status_change",
            {
                "from": previous,
                "to": "completed",
                "actor": "local-user",
                "at": _iso(now),
            },
        )
        await db.commit()
        await db.refresh(session)
        return session_to_view(session)


async def fail_session(session_id: int, *, reason: str = "unhandled error") -> bool:
    """未捕获异常时把进行中的会话标记失败；幂等，非进行中返回 False。"""
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        session = await db.get(AnalysisSession, session_id)
        if session is None or session.status != "in_progress":
            return False
        now = utcnow()
        previous = session.status
        session.status = "failed"
        session.closed_at = now
        await append_event_in_db(
            db,
            session,
            "status_change",
            {
                "from": previous,
                "to": "failed",
                "actor": "system",
                "at": _iso(now),
                "reason": reason,
            },
            actor="system",
        )
        await db.commit()
        return True


async def _detail(db: AsyncSession, session: AnalysisSession) -> dict[str, Any]:
    project = await db.get(ProjectContext, session.project_id)
    model = await db.get(ModelBinding, session.model_id)
    provider = await db.get(ProviderConfig, model.provider_id) if model else None
    return {
        "sessionId": session.session_id,
        "project": {
            "projectId": session.project_id,
            "name": project.name if project else "",
        },
        "entranceKey": session.entrance_key,
        "title": session.title,
        "status": session.status,
        "model": {
            "modelId": session.model_id,
            "modelName": model.model_name if model else "",
            "displayName": model.display_name if model else "",
            "providerId": model.provider_id if model else 0,
            "providerName": provider.name if provider else "",
        },
        "createdAt": session.created_at,
        "updatedAt": session.updated_at,
        "closedAt": session.closed_at,
    }


async def get_session(session_id: int) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        session = await _get_session(db, session_id)
        return await _detail(db, session)


async def list_sessions(
    *,
    project_id: int | None = None,
    status: str | None = None,
    limit: int = 20,
    cursor: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    if status is not None and status not in ("in_progress", "completed", "failed"):
        raise DomainError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "status", "message": "非法会话状态"}],
        )
    after = _parse_session_cursor(cursor)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        statement = select(AnalysisSession)
        if project_id is not None:
            statement = statement.where(AnalysisSession.project_id == project_id)
        if status is not None:
            statement = statement.where(AnalysisSession.status == status)
        if after is not None:
            moment, session_id = after
            statement = statement.where(
                (AnalysisSession.updated_at < moment)
                | (
                    (AnalysisSession.updated_at == moment)
                    & (AnalysisSession.session_id < session_id)
                )
            )
        statement = statement.order_by(
            AnalysisSession.updated_at.desc(), AnalysisSession.session_id.desc()
        ).limit(limit + 1)
        rows = list(await db.scalars(statement))
        has_more = len(rows) > limit
        page = rows[:limit]
        items = [await _detail(db, row) for row in page]
    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_cursor(
            {"updated_at": last.updated_at.isoformat(), "session_id": last.session_id}
        )
    return items, next_cursor


async def list_events_page(
    session_id: int, *, limit: int = 50, cursor: dict[str, Any] | None = None
) -> tuple[list[EventView], str | None]:
    after_id = None
    if cursor is not None:
        raw = cursor.get("event_id")
        if not isinstance(raw, int):
            raise DomainError("validation_error", "游标非法。")
        after_id = raw
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await _get_session(db, session_id)
        statement = select(SessionEvent).where(SessionEvent.session_id == session_id)
        if after_id is not None:
            statement = statement.where(SessionEvent.event_id > after_id)
        statement = statement.order_by(SessionEvent.event_id.asc()).limit(limit + 1)
        rows = list(await db.scalars(statement))
        present = await existing_kb_id_set(db)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = None
    if has_more and page:
        next_cursor = encode_cursor({"event_id": page[-1].event_id})
    views: list[EventView] = []
    for row in page:
        view = event_to_view(row)
        if view["type"] == "knowledge_injection":
            payload = dict(view["payload"] or {})
            payload["items"] = with_kb_deleted(payload.get("items") or [], present) or []
            view["payload"] = payload
        views.append(view)
    return views, next_cursor


def event_to_api(view: EventView) -> dict[str, Any]:
    return {
        "eventId": view["event_id"],
        "sessionId": view["session_id"],
        "type": view["type"],
        "payload": view["payload"],
        "createdAt": _iso(view["created_at"]),
    }


async def append_text_input(session_id: int, *, title: str, text: str) -> EventView:
    cleaned_title = require_text(title, field="title", max_length=200)
    if not text or not text.strip():
        raise DomainError(
            "text_empty",
            "文本内容不能为空。",
            details=[{"field": "text", "message": "正文不能为空白"}],
        )
    if len(text) > PROMPT_MAX_CHARS:
        raise DomainError(
            "text_too_long",
            "文本超过字符上限。",
            details=[
                {
                    "field": "text",
                    "charCount": len(text),
                    "maxChars": PROMPT_MAX_CHARS,
                }
            ],
        )
    return await append_event(
        session_id,
        "input_text",
        {"title": cleaned_title, "text": text, "charCount": len(text)},
    )


async def delete_session(session_id: int) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        session = await _get_session(db, session_id)
        del session

    try:
        trash = storage.move_to_trash(session_id)
    except OSError as exc:
        raise DomainError(
            "session_delete_failed",
            "会话删除失败。",
            status_code=500,
            details=[{"field": "sessionId", "message": "trash rename failed"}],
        ) from exc

    async with sessionmaker() as db:
        row = await db.get(AnalysisSession, session_id)
        if row is None:
            raise DomainError("session_not_found", "会话不存在。", status_code=404)
        try:
            await db.execute(
                delete(SessionEvent).where(SessionEvent.session_id == session_id)
            )
            await db.execute(
                delete(Artifact).where(Artifact.session_id == session_id)
            )
            await db.execute(
                delete(AiCallRecord).where(AiCallRecord.session_id == session_id)
            )
            await db.delete(row)
            await db.commit()
        except Exception:
            await db.rollback()
            _restore_trash(trash)
            raise

    if trash is not None:
        import shutil

        shutil.rmtree(trash, ignore_errors=True)


def _restore_trash(trash) -> None:  # noqa: ANN001
    if trash is None:
        return
    try:
        import os

        target = storage.artifact_dir(int(str(trash.name).split("-", 1)[0]))
        os.replace(trash, target)
    except (OSError, ValueError):  # pragma: no cover - 兜底清理
        logger.warning("failed to restore session trash after rollback")


def _parse_session_cursor(cursor: dict[str, Any] | None):  # noqa: ANN001
    if cursor is None:
        return None
    raw_time = cursor.get("updated_at")
    raw_id = cursor.get("session_id")
    if not isinstance(raw_time, str) or not isinstance(raw_id, int):
        raise DomainError("validation_error", "游标非法。")
    return (
        datetime.fromisoformat(raw_time.replace("Z", "+00:00")).replace(tzinfo=None),
        raw_id,
    )
