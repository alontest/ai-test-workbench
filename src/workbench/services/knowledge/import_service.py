"""知识库导入编排：限额校验 → 暂存 → 解析 → 匹配 → 命名 → 版本化 → 落库。

失败整体回滚：事务、暂存目录与已 rename 的目标目录都不留残留（ADR-105）。
错误与日志只含 id / 文件名 / 行号 / 计数 / 原因码，不含正文（ADR-114）。
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.adapters.fs.knowledge_storage import (
    INDEX_FILE_NAME,
    KbStorage,
    StoredFile,
)
from workbench.api.serialization import to_rfc3339
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.errors import is_unique_violation
from workbench.db.models import KnowledgeBase, KnowledgeEntry, ProjectContext
from workbench.db.repositories import knowledge as knowledge_repo
from workbench.knowledge import (
    KbSettings,
    derive_name,
    get_kb_settings,
    match_bodies,
    name_key,
    parse_index,
)
from workbench.knowledge.types import BodyMatchResult, ParsedIndex
from workbench.services.errors import DomainError

ALLOWED_KB_EXTENSIONS = frozenset({".json", ".md", ".markdown"})
NAME_MAX_CHARS = 200
TITLE_MAX_CHARS = 500
SOURCE_DOC_MAX_CHARS = 100
ANCHOR_MAX_CHARS = 200
BODY_SOURCE_FILE_MAX_CHARS = 255
IMPORT_CONFLICT_RETRY_LIMIT = 1
DEFAULT_ORPHAN_MAX_AGE = timedelta(hours=1)


class UploadedFile(Protocol):
    filename: str | None

    async def read(self, size: int = -1) -> bytes: ...


@dataclass(frozen=True)
class _IncomingFile:
    name: str
    data: bytes
    is_index: bool


def _base_name(original_name: str) -> str:
    return original_name.replace("\\", "/").rsplit("/", 1)[-1]


def _extension(file_name: str) -> str:
    return Path(_base_name(file_name)).suffix.lower()


def _rejected(
    code: str, message: str, details: Sequence[Mapping[str, object]], *, status: int = 400
) -> DomainError:
    return DomainError(code, message, status_code=status, details=details)


def _project_not_found() -> DomainError:
    return DomainError(
        "project_not_found",
        "项目不存在。",
        status_code=404,
        details=[{"field": "projectId", "message": "项目不存在"}],
    )


def _name_conflict() -> DomainError:
    return DomainError(
        "kb_name_conflict",
        "同名知识库正在导入，请稍后重试。",
        status_code=409,
        details=[{"field": "name", "message": "knowledge base name conflict"}],
    )


def _clip(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    return value[:limit]


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


class KnowledgeImportService:
    """把一次 multipart 上传落成知识库版本快照。"""

    def __init__(
        self,
        *,
        sessionmaker=None,  # noqa: ANN001
        storage: KbStorage | None = None,
        kb_settings: KbSettings | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._storage = storage
        self._kb_settings = kb_settings

    @property
    def sessionmaker(self):  # noqa: ANN201
        return self._sessionmaker or get_sessionmaker()

    @property
    def storage(self) -> KbStorage:
        if self._storage is None:
            self._storage = KbStorage()
        return self._storage

    @property
    def kb_settings(self) -> KbSettings:
        return self._kb_settings or get_kb_settings()

    async def import_files(
        self,
        *,
        project_id: int,
        name: str | None,
        files: Sequence[UploadedFile],
    ) -> dict[str, Any]:
        kb = self.kb_settings
        cleaned_name = self._clean_name(name)
        incoming = await self._read_files(files, kb)
        index_file = self._index_file(incoming)

        async with self.sessionmaker() as db:
            if await db.get(ProjectContext, project_id) is None:
                raise _project_not_found()

        parsed = parse_index(index_file.data, settings=kb)
        docs = [(item.name, item.data) for item in incoming if not item.is_index]
        bodies = match_bodies([entry.code for entry in parsed.entries], docs)
        index_sha256 = hashlib.sha256(index_file.data).hexdigest()
        derived = derive_name(cleaned_name, parsed.index_meta, index_sha256)
        key = name_key(derived)
        total_bytes = sum(len(item.data) for item in incoming)
        report_base = self._report_base(
            incoming, parsed, bodies, total_bytes, index_sha256
        )

        last_conflict: DBAPIError | None = None
        for attempt in range(IMPORT_CONFLICT_RETRY_LIMIT + 1):
            token = self.storage.new_token()
            kb_id = uuid.uuid4().hex
            try:
                stored = self.storage.stage(
                    token, [(item.name, item.data) for item in incoming]
                )
                return await self._persist_once(
                    token=token,
                    kb_id=kb_id,
                    project_id=project_id,
                    name=derived,
                    key=key,
                    parsed=parsed,
                    bodies=bodies,
                    stored=stored,
                    report_base=report_base,
                    index_sha256=index_sha256,
                )
            except DBAPIError as exc:
                if not is_unique_violation(exc):
                    raise
                last_conflict = exc
                if attempt >= IMPORT_CONFLICT_RETRY_LIMIT:
                    raise _name_conflict() from exc
            except OSError as exc:
                raise DomainError(
                    "kb_write_failed",
                    "知识库文件写入失败。",
                    status_code=507,
                    details=[{"field": "files", "message": "storage write failed"}],
                ) from exc
            finally:
                self.storage.discard(token)
        raise _name_conflict() from last_conflict

    # --- 校验 ---------------------------------------------------------------

    def _clean_name(self, name: str | None) -> str | None:
        if name is None:
            return None
        cleaned = name.strip()
        if len(cleaned) > NAME_MAX_CHARS:
            raise _rejected(
                "validation_error",
                "请求参数校验失败。",
                [
                    {
                        "field": "name",
                        "message": f"长度不能超过 {NAME_MAX_CHARS}",
                    }
                ],
            )
        return cleaned or None

    async def _read_files(
        self, files: Sequence[UploadedFile], kb: KbSettings
    ) -> list[_IncomingFile]:
        names = [_base_name(upload.filename or "") for upload in files]

        type_errors = [
            {
                "field": "files",
                "fileName": name,
                "message": f"extension {_extension(name) or '(none)'} is not allowed",
            }
            for name in names
            if _extension(name) not in ALLOWED_KB_EXTENSIONS
        ]
        if type_errors:
            raise _rejected("unsupported_file_type", "不支持的文件类型。", type_errors)

        if len(files) > kb.max_files:
            raise _rejected(
                "too_many_files",
                f"一次最多上传 {kb.max_files} 个文件。",
                [
                    {
                        "field": "files",
                        "message": f"count {len(files)}",
                        "limit": kb.max_files,
                    }
                ],
            )

        size_errors = []
        incoming: list[_IncomingFile] = []
        for upload, name in zip(files, names, strict=True):
            is_index = name.casefold() == INDEX_FILE_NAME
            limit = kb.max_index_bytes if is_index else kb.max_file_bytes
            data = await upload.read(limit + 1)
            if len(data) > limit:
                size_errors.append(
                    {
                        "field": "files",
                        "fileName": name,
                        "message": "file too large",
                        "actual": len(data),
                        "limit": limit,
                    }
                )
                continue
            incoming.append(_IncomingFile(name=name, data=data, is_index=is_index))
        if size_errors:
            raise _rejected("file_too_large", "文件超过单文件上限。", size_errors)

        total_bytes = sum(len(item.data) for item in incoming)
        if total_bytes > kb.max_total_bytes:
            raise _rejected(
                "kb_import_too_large",
                "本次上传合计超过上限。",
                [
                    {
                        "field": "files",
                        "message": "total bytes exceeds limit",
                        "actual": total_bytes,
                        "limit": kb.max_total_bytes,
                    }
                ],
                status=413,
            )
        return incoming

    @staticmethod
    def _index_file(incoming: Sequence[_IncomingFile]) -> _IncomingFile:
        indexes = [item for item in incoming if item.is_index]
        if not indexes:
            raise _rejected(
                "index_json_missing",
                "本次上传不含 index.json。",
                [{"field": "files", "message": "index.json is required"}],
            )
        if len(indexes) > 1:
            raise _rejected(
                "index_json_invalid",
                "index.json 不合法，无法导入。",
                [{"field": "files", "message": "multiple index.json files"}],
            )
        return indexes[0]

    # --- 落库 ---------------------------------------------------------------

    def _report_base(
        self,
        incoming: Sequence[_IncomingFile],
        parsed: ParsedIndex,
        bodies: BodyMatchResult,
        total_bytes: int,
        index_sha256: str,
    ) -> dict[str, Any]:
        skipped = [
            {
                "index": item.index,
                "line": item.line,
                "code": item.code,
                "reason": item.reason,
            }
            for item in parsed.report.skipped_entries
        ]
        meta = parsed.index_meta.get("meta")
        meta = meta if isinstance(meta, Mapping) else {}
        graph_fingerprint = parsed.index_meta.get("graph_fingerprint") or meta.get(
            "graph_fingerprint"
        )
        warnings = (
            parsed.report.neighbors_truncated
            + parsed.report.extras_dropped
            + int(parsed.report.skipped_truncated)
        )
        return {
            "files": [
                {"name": item.name, "size": len(item.data), "accepted": True}
                for item in incoming
            ],
            "skippedEntries": skipped,
            "unmatchedFiles": list(bodies.unmatched_files),
            "duplicateBodies": [
                {"code": duplicate.code, "fileName": duplicate.file_name}
                for duplicate in bodies.duplicate_bodies
            ],
            "counts": {
                "files": len(incoming),
                "bytes": total_bytes,
                "entries": len(parsed.entries),
                "skipped": len(parsed.report.skipped_entries),
            },
            "meta": {
                "fingerprint": index_sha256[:16],
                "graphFingerprint": (
                    graph_fingerprint
                    if isinstance(graph_fingerprint, str)
                    else None
                ),
                "warnings": warnings,
            },
        }

    async def _persist_once(
        self,
        *,
        token: str,
        kb_id: str,
        project_id: int,
        name: str,
        key: str,
        parsed: ParsedIndex,
        bodies: BodyMatchResult,
        stored: Sequence[StoredFile],
        report_base: dict[str, Any],
        index_sha256: str,
    ) -> dict[str, Any]:
        async with self.sessionmaker() as db:
            promoted = False
            try:
                version = await knowledge_repo.next_version(
                    db, project_id=project_id, name_key=key
                )
                current = await knowledge_repo.get_current(
                    db, project_id=project_id, name_key=key
                )
                previous_version = current.version if current is not None else None
                self.storage.write_manifest(
                    token,
                    self._manifest(kb_id, name, key, version, parsed, stored),
                )
                self.storage.promote(token, kb_id)
                promoted = True
                if current is not None:
                    current.status = "superseded"
                    current.current_flag = None
                    current.superseded_by_kb_id = kb_id
                    await db.flush()
                report = {
                    **report_base,
                    "versionBumped": previous_version is not None,
                    "previousVersion": previous_version,
                }
                now = utcnow()
                row = KnowledgeBase(
                    kb_id=kb_id,
                    project_id=project_id,
                    name=name,
                    name_key=key,
                    version=version,
                    current_flag="1",
                    status="ready",
                    index_generated_at=parsed.generated_at,
                    entry_count=len(parsed.entries),
                    file_count=len(stored),
                    total_byte_size=sum(item.size for item in stored),
                    source_index_sha256=index_sha256,
                    storage_dir=f"knowledge-bases/{kb_id}",
                    import_report=report,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
                await db.flush()
                await self._write_rows(db, self._entry_rows(kb_id, parsed, bodies))
                await db.commit()
                return {
                    "kb": self._kb_payload(row),
                    "importReport": report,
                }
            except BaseException:
                await db.rollback()
                if promoted:
                    self.storage.remove(kb_id)
                raise

    async def _write_rows(
        self, db: AsyncSession, rows: Sequence[KnowledgeEntry]
    ) -> None:
        await knowledge_repo.bulk_insert_entries(db, rows)

    @staticmethod
    def _entry_rows(
        kb_id: str, parsed: ParsedIndex, bodies: BodyMatchResult
    ) -> list[KnowledgeEntry]:
        rows: list[KnowledgeEntry] = []
        for entry in parsed.entries:
            body = bodies.content_for(entry.code)
            match = bodies.bodies.get(entry.code_key)
            rows.append(
                KnowledgeEntry(
                    kb_id=kb_id,
                    code=entry.code,
                    code_key=entry.code_key,
                    type=entry.type.value,
                    title=entry.title[:TITLE_MAX_CHARS],
                    summary=entry.summary,
                    body=body,
                    body_missing=body is None,
                    body_source_file=(
                        _clip(match.file_name, BODY_SOURCE_FILE_MAX_CHARS)
                        if match is not None
                        else None
                    ),
                    fields=_jsonable(entry.fields),
                    tables=_jsonable(entry.tables),
                    code_paths=_jsonable(entry.code_paths),
                    neighbors=_jsonable(entry.neighbors),
                    extras=_jsonable(entry.extras),
                    source_doc=_clip(entry.source_doc, SOURCE_DOC_MAX_CHARS),
                    anchor=_clip(entry.anchor, ANCHOR_MAX_CHARS),
                    freshness_at=entry.freshness_at,
                    content_digest=entry.content_digest,
                )
            )
        return rows

    @staticmethod
    def _manifest(
        kb_id: str,
        name: str,
        key: str,
        version: int,
        parsed: ParsedIndex,
        stored: Sequence[StoredFile],
    ) -> dict[str, Any]:
        return {
            "kbId": kb_id,
            "name": name,
            "nameKey": key,
            "version": version,
            "indexGeneratedAt": (
                parsed.generated_at.isoformat()
                if parsed.generated_at is not None
                else None
            ),
            "createdAt": utcnow().isoformat(),
            "files": [
                {
                    "name": item.original_name,
                    "storageName": item.storage_name,
                    "sha256": item.sha256,
                    "size": item.size,
                }
                for item in stored
            ],
        }

    @staticmethod
    def _kb_payload(row: KnowledgeBase) -> dict[str, Any]:
        return {
            "kbId": row.kb_id,
            "projectId": row.project_id,
            "name": row.name,
            "version": row.version,
            "current": row.current_flag == "1",
            "status": row.status,
            "generatedAt": to_rfc3339(row.index_generated_at),
            "entryCount": row.entry_count,
            "fileCount": row.file_count,
            "totalByteSize": row.total_byte_size,
            "supersededCount": max(row.version - 1, 0),
            "latestKbId": row.kb_id,
            "createdAt": to_rfc3339(row.created_at),
        }


async def scan_orphan_dirs(
    *,
    sessionmaker=None,  # noqa: ANN001
    storage: KbStorage | None = None,
    max_age: timedelta = DEFAULT_ORPHAN_MAX_AGE,
) -> int:
    """删除目录 mtime 早于 ``max_age`` 且 DB 无对应行的知识库目录。"""
    sm = sessionmaker or get_sessionmaker()
    async with sm() as db:
        known_ids = set(await db.scalars(select(KnowledgeBase.kb_id)))
    return (storage or KbStorage()).scan_orphans(known_ids, max_age=max_age)


__all__ = [
    "ALLOWED_KB_EXTENSIONS",
    "DEFAULT_ORPHAN_MAX_AGE",
    "KnowledgeImportService",
    "UploadedFile",
    "scan_orphan_dirs",
]
