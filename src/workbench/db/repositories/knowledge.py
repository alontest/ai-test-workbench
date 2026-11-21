"""知识库仓储：版本取号、批量写入、检索分页、冲突批量查询与逻辑删除。"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime

from sqlalchemy import and_, delete, func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.db.base import utcnow
from workbench.db.models import KnowledgeBase, KnowledgeEntry

ENTRY_CHUNK_BYTES = 8 * 1024 * 1024
LIKE_ESCAPE = "\\"


async def get(db: AsyncSession, kb_id: str) -> KnowledgeBase | None:
    return await db.get(KnowledgeBase, kb_id)


async def get_many(
    db: AsyncSession, kb_ids: Sequence[str]
) -> dict[str, KnowledgeBase]:
    """按 kbId 集合一次取回，供注入解析使用。"""
    if not kb_ids:
        return {}
    rows = await db.scalars(
        select(KnowledgeBase).where(KnowledgeBase.kb_id.in_(list(kb_ids)))
    )
    return {row.kb_id: row for row in rows}


async def entries_by_codes(
    db: AsyncSession, scopes: Mapping[str, Sequence[str]]
) -> dict[tuple[str, str], KnowledgeEntry]:
    """按 ``(kbId, code_key)`` 集合一次取回条目。"""
    conditions = [
        and_(
            KnowledgeEntry.kb_id == kb_id,
            KnowledgeEntry.code_key.in_(list(code_keys)),
        )
        for kb_id, code_keys in scopes.items()
        if code_keys
    ]
    if not conditions:
        return {}
    rows = await db.scalars(select(KnowledgeEntry).where(or_(*conditions)))
    return {(row.kb_id, row.code_key): row for row in rows}


async def get_current(
    db: AsyncSession, *, project_id: int, name_key: str
) -> KnowledgeBase | None:
    return await db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.name_key == name_key,
            KnowledgeBase.current_flag == "1",
        )
    )


async def list_versions(
    db: AsyncSession, *, project_id: int, name_key: str
) -> list[KnowledgeBase]:
    rows = await db.scalars(
        select(KnowledgeBase)
        .where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.name_key == name_key,
        )
        .order_by(KnowledgeBase.version.asc())
    )
    return list(rows)


async def next_version(
    db: AsyncSession, *, project_id: int, name_key: str
) -> int:
    """行锁取号：MySQL ``FOR UPDATE``；SQLite 串行写不需要显式锁。"""
    statement = (
        select(KnowledgeBase.version)
        .where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.name_key == name_key,
        )
        .order_by(KnowledgeBase.version.desc())
        .limit(1)
    )
    if db.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()
    current = await db.scalar(statement)
    return (current or 0) + 1


def _entry_size(entry: KnowledgeEntry) -> int:
    size = len(entry.code.encode("utf-8")) + len(entry.title.encode("utf-8"))
    for text in (entry.summary, entry.body):
        if text:
            size += len(text.encode("utf-8"))
    for payload in (
        entry.fields,
        entry.tables,
        entry.code_paths,
        entry.neighbors,
        entry.extras,
    ):
        if payload is not None:
            size += len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return size


def _entry_row(entry: KnowledgeEntry) -> dict[str, object]:
    row = {column.name: getattr(entry, column.name) for column in KnowledgeEntry.__table__.columns}
    if row.get("created_at") is None:
        row["created_at"] = utcnow()
    if row.get("body_missing") is None:
        row["body_missing"] = True
    if row.get("summary") is None:
        row["summary"] = ""
    return row


async def bulk_insert_entries(
    db: AsyncSession, entries: Sequence[KnowledgeEntry]
) -> None:
    """按累计 ≤8MB 分块 ``executemany``，避免逐行往返。"""
    chunk: list[dict[str, object]] = []
    chunk_bytes = 0
    for entry in entries:
        row = _entry_row(entry)
        size = _entry_size(entry)
        if chunk and chunk_bytes + size > ENTRY_CHUNK_BYTES:
            await db.execute(insert(KnowledgeEntry), chunk)
            chunk = []
            chunk_bytes = 0
        chunk.append(row)
        chunk_bytes += size
    if chunk:
        await db.execute(insert(KnowledgeEntry), chunk)


def _escape_like(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _entry_conditions(
    *,
    project_id: int | None,
    kb_id: str | None,
    entry_type: str | None,
    q: str | None,
    include_superseded: bool,
) -> list[object]:
    conditions: list[object] = []
    if project_id is not None:
        conditions.append(KnowledgeBase.project_id == project_id)
    if kb_id is not None:
        conditions.append(KnowledgeEntry.kb_id == kb_id)
    elif not include_superseded:
        conditions.append(KnowledgeBase.current_flag == "1")
    if entry_type is not None:
        conditions.append(KnowledgeEntry.type == entry_type)
    if q:
        pattern = f"%{_escape_like(q)}%"
        conditions.append(
            or_(
                KnowledgeEntry.code.ilike(pattern, escape=LIKE_ESCAPE),
                KnowledgeEntry.title.ilike(pattern, escape=LIKE_ESCAPE),
                KnowledgeEntry.summary.ilike(pattern, escape=LIKE_ESCAPE),
                KnowledgeEntry.body.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    return conditions


async def list_entries(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    kb_id: str | None = None,
    entry_type: str | None = None,
    q: str | None = None,
    include_superseded: bool = False,
    limit: int,
    after: tuple[str, str] | None = None,
) -> list[KnowledgeEntry]:
    statement = select(KnowledgeEntry).join(
        KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id
    )
    conditions = _entry_conditions(
        project_id=project_id,
        kb_id=kb_id,
        entry_type=entry_type,
        q=q,
        include_superseded=include_superseded,
    )
    if conditions:
        statement = statement.where(and_(*conditions))
    if after is not None:
        code_key, entry_id = after
        statement = statement.where(
            or_(
                KnowledgeEntry.code_key > code_key,
                and_(
                    KnowledgeEntry.code_key == code_key,
                    KnowledgeEntry.entry_id > entry_id,
                ),
            )
        )
    statement = statement.order_by(
        KnowledgeEntry.code_key.asc(), KnowledgeEntry.entry_id.asc()
    ).limit(limit)
    return list(await db.scalars(statement))


async def counts_by_type(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    kb_id: str | None = None,
    q: str | None = None,
    include_superseded: bool = False,
) -> dict[str, int]:
    """忽略 ``type`` 条件、共用其他条件一次聚合。"""
    conditions = _entry_conditions(
        project_id=project_id,
        kb_id=kb_id,
        entry_type=None,
        q=q,
        include_superseded=include_superseded,
    )
    statement = (
        select(KnowledgeEntry.type, func.count())
        .join(KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id)
        .group_by(KnowledgeEntry.type)
    )
    if conditions:
        statement = statement.where(and_(*conditions))
    result = await db.execute(statement)
    return {row[0]: int(row[1]) for row in result.all()}


async def find_conflicts(
    db: AsyncSession,
    *,
    project_id: int,
    code_keys: Sequence[str],
    exclude_kb_id: str | None = None,
    limit: int,
) -> list[tuple[KnowledgeEntry, KnowledgeBase]]:
    """按 ``code_key IN (...)`` 批量查询，不做逐行 N+1。"""
    if not code_keys:
        return []
    statement = (
        select(KnowledgeEntry, KnowledgeBase)
        .join(KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id)
        .where(
            KnowledgeBase.project_id == project_id,
            KnowledgeEntry.code_key.in_(list(code_keys)),
        )
        .order_by(KnowledgeEntry.code_key.asc(), KnowledgeBase.version.desc())
        .limit(limit)
    )
    if exclude_kb_id is not None:
        statement = statement.where(KnowledgeBase.kb_id != exclude_kb_id)
    result = await db.execute(statement)
    return [(row[0], row[1]) for row in result.all()]


async def delete_logical(
    db: AsyncSession, *, project_id: int, name_key: str
) -> int:
    """删除逻辑库全部版本；条目由 ``ON DELETE CASCADE`` 跟随。"""
    result = await db.execute(
        delete(KnowledgeBase).where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.name_key == name_key,
        )
    )
    return result.rowcount or 0


async def list_bases(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    include_superseded: bool = False,
    limit: int,
    after: tuple[datetime, str] | None = None,
) -> list[KnowledgeBase]:
    statement = select(KnowledgeBase)
    if project_id is not None:
        statement = statement.where(KnowledgeBase.project_id == project_id)
    if not include_superseded:
        statement = statement.where(KnowledgeBase.current_flag == "1")
    if after is not None:
        moment, kb_id = after
        statement = statement.where(
            or_(
                KnowledgeBase.updated_at < moment,
                and_(
                    KnowledgeBase.updated_at == moment,
                    KnowledgeBase.kb_id < kb_id,
                ),
            )
        )
    statement = statement.order_by(
        KnowledgeBase.updated_at.desc(), KnowledgeBase.kb_id.desc()
    ).limit(limit)
    return list(await db.scalars(statement))


__all__ = [
    "ENTRY_CHUNK_BYTES",
    "bulk_insert_entries",
    "counts_by_type",
    "delete_logical",
    "entries_by_codes",
    "find_conflicts",
    "get",
    "get_current",
    "get_many",
    "list_bases",
    "list_entries",
    "list_versions",
    "next_version",
]
