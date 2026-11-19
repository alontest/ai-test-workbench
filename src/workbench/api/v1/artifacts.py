"""会话制品上传、元数据与内容接口。"""

from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy import select

from workbench.adapters.fs import storage
from workbench.api.deps import require_same_origin
from workbench.api.serialization import to_rfc3339
from workbench.core.constants import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    MAX_ARTIFACT_BYTES,
    MAX_FILES_PER_UPLOAD,
    MIME_TYPE_BY_EXTENSION,
    PREVIEW_MAX_BYTES,
)
from workbench.db.engine import get_sessionmaker
from workbench.db.models import Artifact, SessionEvent
from workbench.services import artifacts as artifacts_service
from workbench.services.errors import DomainError

router = APIRouter(tags=["artifacts"], dependencies=[Depends(require_same_origin)])


def _invalid(code: str, message: str, details) -> DomainError:  # noqa: ANN001
    return DomainError(code, message, details=details)


def _file_extension(file_name: str) -> str:
    return Path(file_name.replace("\\", "/")).suffix.lower()


def _artifact_payload(view: dict) -> dict:
    return {
        "artifactId": view["artifact_id"],
        "sessionId": view["session_id"],
        "kind": view["kind"],
        "fileName": view["file_name"],
        "mimeType": view["mime_type"],
        "byteSize": view["byte_size"],
        "createdAt": to_rfc3339(view["created_at"]),
    }


def _event_payload(row: SessionEvent) -> dict:
    return {
        "eventId": row.event_id,
        "sessionId": row.session_id,
        "type": row.type,
        "payload": dict(row.payload or {}),
        "createdAt": to_rfc3339(row.created_at),
    }


@router.post("/sessions/{session_id}/artifacts", status_code=201)
async def upload_artifacts(
    session_id: int, files: list[UploadFile] = File(...)
) -> dict[str, object]:
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise _invalid(
            "too_many_files",
            f"一次最多上传 {MAX_FILES_PER_UPLOAD} 个文件。",
            [{"field": "files", "message": f"count {len(files)}"}],
        )

    type_errors = []
    for upload in files:
        name = Path((upload.filename or "").replace("\\", "/")).name
        extension = _file_extension(name)
        if extension not in ALLOWED_ARTIFACT_EXTENSIONS:
            type_errors.append(
                {
                    "field": "files",
                    "fileName": name,
                    "message": f"extension {extension or '(none)'} is not allowed",
                }
            )
    if type_errors:
        raise _invalid("file_type_not_allowed", "不支持的文件类型。", type_errors)

    buffered: list[tuple[str, bytes]] = []
    size_errors = []
    for upload in files:
        name = Path((upload.filename or "").replace("\\", "/")).name
        data = await upload.read(MAX_ARTIFACT_BYTES + 1)
        if len(data) > MAX_ARTIFACT_BYTES:
            size_errors.append(
                {"field": "files", "fileName": name, "message": "超过 10MB"}
            )
            continue
        buffered.append((name, data))
    if size_errors:
        raise _invalid("file_too_large", "文件超过 10MB。", size_errors)

    views = []
    for name, data in buffered:
        view = await artifacts_service.save(
            session_id,
            file_name=name,
            source=io.BytesIO(data),
            claimed_content_type=None,
        )
        views.append(view)

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        rows = list(
            await db.scalars(
                select(SessionEvent)
                .where(
                    SessionEvent.session_id == session_id,
                    SessionEvent.type == "artifact",
                )
                .order_by(SessionEvent.event_id.desc())
                .limit(len(views))
            )
        )
    rows.reverse()
    return {
        "items": [_artifact_payload(view) for view in views],
        "events": [_event_payload(row) for row in rows],
    }


async def _load_artifact(artifact_id: int) -> Artifact:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await db.get(Artifact, artifact_id)
        if row is None:
            raise _not_found()
        return row


def _not_found() -> DomainError:
    return DomainError(
        "artifact_not_found",
        "制品不存在。",
        status_code=404,
        details=[{"field": "artifactId", "message": "artifact not found"}],
    )


@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: int) -> dict[str, object]:
    row = await _load_artifact(artifact_id)
    return {
        "artifactId": row.artifact_id,
        "sessionId": row.session_id,
        "kind": row.kind,
        "fileName": row.file_name,
        "mimeType": row.mime_type,
        "byteSize": row.byte_size,
        "createdAt": to_rfc3339(row.created_at),
    }


def _content_type(row: Artifact) -> str:
    extension = _file_extension(row.file_name)
    mime = MIME_TYPE_BY_EXTENSION.get(extension, row.mime_type or "text/plain")
    if mime.startswith("text/") or mime in ("application/json", "application/sql", "application/yaml"):
        mime = f"{mime}; charset=utf-8"
    return mime


def _disposition(mode: str, file_name: str) -> str:
    from urllib.parse import quote

    fallback = "".join(ch if ch.isascii() and ch not in '"\\' else "_" for ch in file_name)
    encoded = quote(file_name, safe="")
    return (
        f'{mode}; filename="{fallback}"; '
        f"filename*=UTF-8''{encoded}"
    )


@router.get("/artifacts/{artifact_id}/content")
async def get_artifact_content(
    artifact_id: int,
    mode: str = Query("inline", pattern="^(inline|download)$"),
    max_bytes: int | None = None,
) -> Response:
    row = await _load_artifact(artifact_id)
    if max_bytes is not None:
        if max_bytes < 1 or max_bytes > PREVIEW_MAX_BYTES:
            raise _invalid(
                "validation_error",
                "预览字节数非法。",
                [{"field": "max_bytes", "message": f"必须在 1–{PREVIEW_MAX_BYTES}"}],
            )
    try:
        path = storage.safe_artifact_path(row.session_id, row.relative_path)
    except storage.ArtifactNotFound as exc:
        plain = storage.artifact_dir(row.session_id) / row.storage_name
        if not plain.exists():
            raise DomainError(
                "artifact_file_missing",
                "制品文件不存在。",
                status_code=410,
                details=[{"field": "artifactId", "message": "file missing"}],
            ) from exc
        raise _not_found() from exc

    data = path.read_bytes()
    if mode == "inline":
        data = data[: max_bytes or PREVIEW_MAX_BYTES]
    return Response(
        content=data,
        media_type=_content_type(row),
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": _disposition(
                "inline" if mode == "inline" else "attachment", row.file_name
            ),
        },
    )
