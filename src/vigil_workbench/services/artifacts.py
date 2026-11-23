"""制品保存：ADR-041 冻结签名 save。"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Literal, TypedDict

from sqlalchemy import select

from vigil_workbench.adapters.fs import storage
from vigil_workbench.core.constants import (
    ALLOWED_ARTIFACT_EXTENSIONS,
    DUPLICATE_NAME_RETRY_LIMIT,
    MAX_ARTIFACT_BYTES,
    MIME_TYPE_BY_EXTENSION,
)
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.repositories import artifacts as artifacts_repo
from vigil_workbench.db.models import AnalysisSession, Artifact
from vigil_workbench.services.errors import DomainError
from vigil_workbench.services.sessions import append_event_in_db, _next_timestamp

_CHUNK_SIZE = 1024 * 1024


class ArtifactView(TypedDict):
    artifact_id: int
    session_id: int
    kind: Literal["upload", "generated"]
    file_name: str
    mime_type: str
    byte_size: int
    created_at: datetime


def _extension(file_name: str) -> str:
    return Path(file_name).suffix.lower()


def _validate_extension(file_name: str) -> str:
    extension = _extension(file_name)
    if extension not in ALLOWED_ARTIFACT_EXTENSIONS:
        raise DomainError(
            "file_type_not_allowed",
            "不支持的文件类型。",
            details=[{"field": "file_name", "message": f"extension {extension or '(none)'} is not allowed"}],
        )
    return extension


def _candidate_names(file_name: str, existing: set[str]) -> list[str]:
    path = Path(file_name)
    stem, suffix = path.stem, path.suffix
    candidate = file_name
    if candidate.casefold() not in existing:
        return [candidate]
    names = [candidate]
    for index in range(1, DUPLICATE_NAME_RETRY_LIMIT + 1):
        candidate = f"{stem}-{index}{suffix}"
        if candidate.casefold() not in existing:
            names.append(candidate)
            return names
    names.append(f"{stem}-{uuid.uuid4().hex[:8]}{suffix}")
    return names


def _view(row: Artifact) -> ArtifactView:
    return {
        "artifact_id": row.artifact_id,
        "session_id": row.session_id,
        "kind": row.kind,  # type: ignore[typeddict-item]
        "file_name": row.file_name,
        "mime_type": row.mime_type,
        "byte_size": row.byte_size,
        "created_at": row.created_at,
    }


def _sanitize_name(file_name: str) -> str:
    """客户端文件名只保留 basename，绝不参与路径拼接。"""
    normalized = file_name.replace("\\", "/")
    return Path(normalized).name


async def save(
    session_id: int,
    *,
    file_name: str,
    source: BinaryIO,
    claimed_content_type: str | None = None,
    kind: Literal["upload", "generated"] = "upload",
) -> ArtifactView:
    file_name = _sanitize_name(file_name)
    extension = _validate_extension(file_name)
    if kind not in ("upload", "generated"):
        raise DomainError("validation_error", "制品类型非法。")

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

        tmp = storage.tmp_dir()
        tmp.mkdir(parents=True, exist_ok=True)
        tmp_path = tmp / f"{uuid.uuid4().hex}.part"
        target: Path | None = None
        try:
            size = _write_limited(source, tmp_path)
            if size > MAX_ARTIFACT_BYTES:
                raise DomainError(
                    "file_too_large",
                    "文件超过 10MB。",
                    details=[{"field": "file_name", "message": f"byteSize {size}"}],
                )

            existing = await artifacts_repo.existing_file_name_keys(db, session_id)
            final_name = _candidate_names(file_name, existing)[-1]
            storage_name = f"{uuid.uuid4().hex}{extension}"
            directory = storage.ensure_session_dir(session_id)
            target = directory / storage_name
            os.replace(tmp_path, target)

            now = utcnow()
            row = Artifact(
                session_id=session_id,
                kind=kind,
                file_name=final_name,
                file_name_key=final_name.casefold(),
                storage_name=storage_name,
                relative_path=f"sessions/{session_id}/{storage_name}",
                mime_type=MIME_TYPE_BY_EXTENSION.get(extension, "application/octet-stream"),
                byte_size=size,
                created_at=now,
            )
            db.add(row)
            await db.flush()
            await append_event_in_db(
                db,
                session,
                "artifact",
                {
                    "artifactId": row.artifact_id,
                    "fileName": final_name,
                    "byteSize": size,
                    "mimeType": row.mime_type,
                    "kind": kind,
                },
            )
            session.updated_at = _next_timestamp(session.updated_at, now)
            await db.commit()
            await db.refresh(row)
            return _view(row)
        except DomainError:
            await db.rollback()
            _cleanup(tmp_path, target)
            raise
        except OSError as exc:
            await db.rollback()
            _cleanup(tmp_path, target)
            raise DomainError(
                "artifact_write_failed",
                "制品写入失败。",
                status_code=507,
                details=[{"field": "file_name", "message": "disk write failed"}],
            ) from exc
        except Exception:
            await db.rollback()
            _cleanup(tmp_path, target)
            raise


def _write_limited(source: BinaryIO, path: Path) -> int:
    size = 0
    with path.open("wb") as handle:
        while True:
            chunk = source.read(_CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            handle.write(chunk)
            if size > MAX_ARTIFACT_BYTES:
                break
    return size


def _cleanup(tmp_path: Path, target: Path | None) -> None:
    for path in (tmp_path, target):
        if path is None:
            continue
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError:  # pragma: no cover - 清理失败由启动孤儿扫描兜底
            continue
