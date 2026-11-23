"""知识库查询服务：列表/详情/版本、条目浏览与检索、徽标与冲突提示。

全部只读：不改库表、不改批次 A/B 的写入仓储。分页统一 ``limit + cursor``，
游标不透明（base64url），与 core 的 ``api/pagination.py`` 同一口径。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.api.pagination import encode_cursor
from vigil_workbench.api.serialization import to_rfc3339
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.models import KnowledgeBase, KnowledgeEntry, ProjectContext
from vigil_workbench.db.repositories import knowledge as knowledge_repo
from vigil_workbench.db.repositories import knowledge_query
from vigil_workbench.knowledge import get_kb_settings
from vigil_workbench.knowledge.config import KbSettings
from vigil_workbench.knowledge.types import EntryType
from vigil_workbench.services.errors import DomainError

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
Q_MAX_CHARS = 100
ENTRY_TYPES = frozenset(item.value for item in EntryType)


def _project_not_found() -> DomainError:
    return DomainError(
        "project_not_found",
        "项目不存在。",
        status_code=404,
        details=[{"field": "projectId", "message": "项目不存在"}],
    )


def _kb_not_found() -> DomainError:
    return DomainError(
        "kb_not_found",
        "知识库不存在。",
        status_code=404,
        details=[{"field": "kbId", "message": "知识库不存在"}],
    )


def _entry_not_found() -> DomainError:
    return DomainError(
        "entry_not_found",
        "条目不存在。",
        status_code=404,
        details=[{"field": "entryId", "message": "条目不存在"}],
    )


def _invalid(field: str, message: str) -> DomainError:
    return DomainError(
        "validation_error",
        "请求参数校验失败。",
        details=[{"field": field, "message": message}],
    )


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= MAX_LIMIT:
        raise _invalid("limit", f"必须为 1–{MAX_LIMIT}")


def _validate_entry_type(entry_type: str | None) -> None:
    if entry_type is not None and entry_type not in ENTRY_TYPES:
        raise _invalid("type", "非法条目类型")


def _validate_q(q: str | None) -> None:
    if q is not None and not 1 <= len(q) <= Q_MAX_CHARS:
        raise _invalid("q", f"长度必须为 1–{Q_MAX_CHARS}")


def _parse_entry_cursor(
    cursor: Mapping[str, Any] | None,
) -> tuple[int, str, str] | None:
    if cursor is None:
        return None
    rank = cursor.get("rank")
    code = cursor.get("code")
    entry_id = cursor.get("entryId")
    if (
        not isinstance(rank, int)
        or isinstance(rank, bool)
        or not isinstance(code, str)
        or not isinstance(entry_id, str)
    ):
        raise _invalid("cursor", "invalid cursor")
    return rank, code, entry_id


def _parse_base_cursor(
    cursor: Mapping[str, Any] | None,
) -> tuple[datetime, str] | None:
    if cursor is None:
        return None
    moment = cursor.get("updatedAt")
    kb_id = cursor.get("kbId")
    if not isinstance(moment, str) or not isinstance(kb_id, str):
        raise _invalid("cursor", "invalid cursor")
    try:
        parsed = datetime.fromisoformat(moment)
    except ValueError as exc:
        raise _invalid("cursor", "invalid cursor") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed, kb_id


def _freshness(
    at: datetime | None, *, now: datetime, stale_days: int
) -> dict[str, Any]:
    if at is None:
        return {"at": None, "state": "unknown"}
    state = "stale" if at < now - timedelta(days=stale_days) else "fresh"
    return {"at": to_rfc3339(at), "state": state}


ConflictTarget = tuple[str, int, str, str]


def _conflict_sources(
    rows: Sequence[tuple[int, str, str, KnowledgeBase]],
    targets: Sequence[ConflictTarget],
    limit: int,
) -> dict[str, list[dict[str, Any]]]:
    """按目标条目逐条比对摘要摘要；同编号不同当前库各自独立判定。"""
    wanted: dict[tuple[int, str], list[tuple[str, str]]] = {}
    for key, project_id, code_key, digest in targets:
        wanted.setdefault((project_id, code_key), []).append((key, digest))
    sources: dict[str, list[dict[str, Any]]] = {key: [] for key, *_rest in targets}
    for code_key, row_digest, project_id, kb in rows:
        for key, digest in wanted.get((project_id, code_key), ()):
            if row_digest == digest:
                continue
            bucket = sources[key]
            if len(bucket) >= limit:
                continue
            bucket.append(
                {
                    "kbName": kb.name,
                    "version": kb.version,
                    "generatedAt": to_rfc3339(kb.index_generated_at),
                }
            )
    return sources


class KnowledgeQueryService:
    """浏览 API 与后续注入候选共用的只读服务。"""

    def __init__(
        self,
        *,
        sessionmaker=None,  # noqa: ANN001
        kb_settings: KbSettings | None = None,
        now: datetime | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._kb_settings = kb_settings
        self._now = now

    @property
    def sessionmaker(self):  # noqa: ANN201
        return self._sessionmaker or get_sessionmaker()

    @property
    def kb_settings(self) -> KbSettings:
        return self._kb_settings or get_kb_settings()

    def _clock(self) -> datetime:
        return self._now or utcnow()

    # --- 知识库 -------------------------------------------------------------

    async def list_bases(
        self,
        *,
        project_id: int | None = None,
        include_superseded: bool = False,
        limit: int = DEFAULT_LIMIT,
        cursor: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_limit(limit)
        after = _parse_base_cursor(cursor)
        async with self.sessionmaker() as db:
            if project_id is not None:
                await self._require_project(db, project_id)
            rows = await knowledge_query.list_bases_page(
                db,
                project_id=project_id,
                include_superseded=include_superseded,
                limit=limit + 1,
                after=after,
            )
            page = rows[:limit]
            latest = await knowledge_query.current_bases(
                db,
                scopes=[(kb.project_id, kb.name_key) for kb, _ in page],
            )
        items = [
            _base_payload(kb, project, latest.get((kb.project_id, kb.name_key)))
            for kb, project in page
        ]
        next_cursor = None
        if len(rows) > limit and page:
            last, _project = page[-1]
            next_cursor = encode_cursor(
                {"updatedAt": last.updated_at.isoformat(), "kbId": last.kb_id}
            )
        return {"items": items, "nextCursor": next_cursor}

    async def get_base(self, kb_id: str) -> dict[str, Any]:
        async with self.sessionmaker() as db:
            kb = await knowledge_repo.get(db, kb_id)
            if kb is None:
                raise _kb_not_found()
            project = await db.get(ProjectContext, kb.project_id)
            versions = await knowledge_repo.list_versions(
                db, project_id=kb.project_id, name_key=kb.name_key
            )
        latest = _latest_of(versions)
        superseded_by = None
        if kb.status == "superseded" and kb.superseded_by_kb_id:
            successor = next(
                (row for row in versions if row.kb_id == kb.superseded_by_kb_id),
                None,
            )
            if successor is not None:
                superseded_by = {
                    "kbId": successor.kb_id,
                    "version": successor.version,
                }
        return {
            "kb": _version_payload(kb),
            "project": _project_payload(project),
            "versions": [_version_item(row) for row in versions],
            "importReport": kb.import_report or {},
            "latestKbId": latest.kb_id if latest is not None else kb.kb_id,
            "supersededBy": superseded_by,
        }

    async def list_versions(self, kb_id: str) -> dict[str, Any]:
        async with self.sessionmaker() as db:
            kb = await knowledge_repo.get(db, kb_id)
            if kb is None:
                raise _kb_not_found()
            versions = await knowledge_repo.list_versions(
                db, project_id=kb.project_id, name_key=kb.name_key
            )
        latest = _latest_of(versions)
        return {
            "items": [_version_item(row) for row in versions],
            "latestKbId": latest.kb_id if latest is not None else kb.kb_id,
            "nextCursor": None,
        }

    # --- 条目 ---------------------------------------------------------------

    async def search_entries(
        self,
        *,
        project_id: int | None = None,
        kb_id: str | None = None,
        entry_type: str | None = None,
        q: str | None = None,
        include_superseded: bool = False,
        limit: int = DEFAULT_LIMIT,
        cursor: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_limit(limit)
        _validate_entry_type(entry_type)
        _validate_q(q)
        after = _parse_entry_cursor(cursor)
        settings = self.kb_settings
        now = self._clock()
        async with self.sessionmaker() as db:
            rows = await knowledge_query.search_entries_page(
                db,
                project_id=project_id,
                kb_id=kb_id,
                entry_type=entry_type,
                q=q,
                include_superseded=include_superseded,
                limit=limit + 1,
                after=after,
            )
            counts = await knowledge_query.counts_by_type(
                db,
                project_id=project_id,
                kb_id=kb_id,
                q=q,
                include_superseded=include_superseded,
            )
            if not rows and not counts:
                await self._ensure_scope(db, project_id=project_id, kb_id=kb_id)
            page = rows[:limit]
            targets = [
                (entry.entry_id, kb.project_id, entry.code_key, entry.content_digest)
                for entry, kb, _rank in page
            ]
            scopes = {
                (project_id, code_key)
                for _key, project_id, code_key, _digest in targets
            }
            conflicts = _conflict_sources(
                await knowledge_query.list_conflict_rows(db, scopes=list(scopes)),
                targets,
                settings.conflict_sources,
            )
        items = [
            _entry_item(
                entry,
                kb,
                conflict_sources=conflicts.get(entry.entry_id, []),
                now=now,
                stale_days=settings.stale_days,
            )
            for entry, kb, _rank in page
        ]
        counts_by_type = {item.value: counts.get(item.value, 0) for item in EntryType}
        total = (
            counts_by_type.get(entry_type, 0)
            if entry_type is not None
            else sum(counts_by_type.values())
        )
        next_cursor = None
        if len(rows) > limit and page:
            last, _kb, rank = page[-1]
            next_cursor = encode_cursor(
                {"rank": rank, "code": last.code_key, "entryId": last.entry_id}
            )
        return {
            "items": items,
            "countsByType": counts_by_type,
            "total": total,
            "nextCursor": next_cursor,
        }

    async def get_entry(self, entry_id: str) -> dict[str, Any]:
        settings = self.kb_settings
        now = self._clock()
        async with self.sessionmaker() as db:
            entry = await db.get(KnowledgeEntry, entry_id)
            if entry is None:
                raise _entry_not_found()
            kb = await db.get(KnowledgeBase, entry.kb_id)
            if kb is None:
                raise _entry_not_found()
            versions = await knowledge_repo.list_versions(
                db, project_id=kb.project_id, name_key=kb.name_key
            )
            neighbors = await self._resolve_neighbors(db, kb, entry)
            conflicts = _conflict_sources(
                await knowledge_query.list_conflict_rows(
                    db, scopes=[(kb.project_id, entry.code_key)]
                ),
                [
                    (
                        entry.entry_id,
                        kb.project_id,
                        entry.code_key,
                        entry.content_digest,
                    )
                ],
                settings.conflict_sources,
            ).get(entry.entry_id, [])
        latest = _latest_of(versions)
        return {
            "entryId": entry.entry_id,
            "code": entry.code,
            "title": entry.title,
            "type": entry.type,
            "kb": _entry_kb_payload(kb, latest),
            "summary": entry.summary,
            "body": None if entry.body_missing else entry.body,
            "bodyMissing": bool(entry.body_missing),
            "bodySourceFile": entry.body_source_file,
            "sourceDoc": entry.source_doc,
            "anchor": entry.anchor,
            "fields": entry.fields or {},
            "tables": entry.tables or [],
            "codePaths": entry.code_paths or [],
            "neighbors": neighbors,
            "freshness": _freshness(
                entry.freshness_at, now=now, stale_days=settings.stale_days
            ),
            "conflicts": conflicts,
            "createdAt": to_rfc3339(entry.created_at),
        }

    async def _resolve_neighbors(
        self, db: AsyncSession, kb: KnowledgeBase, entry: KnowledgeEntry
    ) -> list[dict[str, Any]]:
        raw = entry.neighbors if isinstance(entry.neighbors, list) else []
        codes: list[str] = []
        for item in raw:
            if isinstance(item, Mapping):
                code = item.get("id")
                if isinstance(code, str) and code:
                    codes.append(code.casefold())
        resolved = await knowledge_query.resolve_neighbor_entries(
            db, project_id=kb.project_id, code_keys=codes
        )
        neighbors: list[dict[str, Any]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            code = item.get("id")
            if not isinstance(code, str) or not code:
                continue
            found = resolved.get(code.casefold())
            neighbor: dict[str, Any] = {"code": code, "exists": found is not None}
            if found is not None:
                neighbor.update(
                    {
                        "title": found.title,
                        "entryId": found.entry_id,
                        "kbId": found.kb_id,
                    }
                )
            neighbors.append(neighbor)
        return neighbors

    # --- 校验 ---------------------------------------------------------------

    async def _require_project(self, db: AsyncSession, project_id: int) -> None:
        if await db.get(ProjectContext, project_id) is None:
            raise _project_not_found()

    async def _ensure_scope(
        self,
        db: AsyncSession,
        *,
        project_id: int | None,
        kb_id: str | None,
    ) -> None:
        """空结果时才验证作用域，保证常规查询的 SQL 次数为常数。"""
        if kb_id is not None and await knowledge_repo.get(db, kb_id) is None:
            raise _kb_not_found()
        if project_id is not None:
            await self._require_project(db, project_id)


def _latest_of(versions: Sequence[KnowledgeBase]) -> KnowledgeBase | None:
    for row in versions:
        if row.current_flag == "1":
            return row
    return None


def _project_payload(project: ProjectContext | None) -> dict[str, Any]:
    if project is None:
        return {"id": None, "name": None}
    return {"id": project.project_id, "name": project.name}


def _base_payload(
    kb: KnowledgeBase,
    project: ProjectContext,
    latest: KnowledgeBase | None,
) -> dict[str, Any]:
    return {
        "kbId": kb.kb_id,
        "projectId": kb.project_id,
        "name": kb.name,
        "version": kb.version,
        "current": kb.current_flag == "1",
        "status": kb.status,
        "generatedAt": to_rfc3339(kb.index_generated_at),
        "entryCount": kb.entry_count,
        "fileCount": kb.file_count,
        "totalByteSize": kb.total_byte_size,
        "supersededCount": max(kb.version - 1, 0),
        "latestKbId": latest.kb_id if latest is not None else kb.kb_id,
        "createdAt": to_rfc3339(kb.created_at),
        "project": _project_payload(project),
    }


def _version_payload(kb: KnowledgeBase) -> dict[str, Any]:
    return {
        "kbId": kb.kb_id,
        "name": kb.name,
        "version": kb.version,
        "current": kb.current_flag == "1",
        "status": kb.status,
        "generatedAt": to_rfc3339(kb.index_generated_at),
        "entryCount": kb.entry_count,
        "fileCount": kb.file_count,
        "createdAt": to_rfc3339(kb.created_at),
    }


def _version_item(kb: KnowledgeBase) -> dict[str, Any]:
    return {
        "kbId": kb.kb_id,
        "version": kb.version,
        "current": kb.current_flag == "1",
        "status": kb.status,
        "generatedAt": to_rfc3339(kb.index_generated_at),
        "entryCount": kb.entry_count,
        "fileCount": kb.file_count,
        "createdAt": to_rfc3339(kb.created_at),
    }


def _entry_kb_payload(
    kb: KnowledgeBase, latest: KnowledgeBase | None
) -> dict[str, Any]:
    return {
        "kbId": kb.kb_id,
        "name": kb.name,
        "version": kb.version,
        "generatedAt": to_rfc3339(kb.index_generated_at),
        "current": kb.current_flag == "1",
        "superseded": kb.status == "superseded",
        "latestKbId": latest.kb_id if latest is not None else kb.kb_id,
    }


def _entry_item(
    entry: KnowledgeEntry,
    kb: KnowledgeBase,
    *,
    conflict_sources: Sequence[Mapping[str, Any]],
    now: datetime,
    stale_days: int,
) -> dict[str, Any]:
    return {
        "entryId": entry.entry_id,
        "code": entry.code,
        "title": entry.title,
        "type": entry.type,
        "kbId": kb.kb_id,
        "kbName": kb.name,
        "kbVersion": kb.version,
        "superseded": kb.status == "superseded",
        "bodyMissing": bool(entry.body_missing),
        "freshness": _freshness(entry.freshness_at, now=now, stale_days=stale_days),
        "conflict": {"hasConflict": bool(conflict_sources)},
    }


__all__ = [
    "DEFAULT_LIMIT",
    "ENTRY_TYPES",
    "KnowledgeQueryService",
    "MAX_LIMIT",
    "Q_MAX_CHARS",
]
