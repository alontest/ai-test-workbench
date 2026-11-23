"""知识库浏览与检索的只读查询。

与批次 A 的写入仓储分开，避免把排序/游标语义塞进导入路径。
所有「多条目」查询都按集合一次取回，不做逐行 N+1。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.db.models import KnowledgeBase, KnowledgeEntry, ProjectContext

LIKE_ESCAPE = "\\"

EntryRow = tuple[KnowledgeEntry, KnowledgeBase, int]
BaseRow = tuple[KnowledgeBase, ProjectContext]


def escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _contains(value: str) -> str:
    return f"%{escape_like(value)}%"


def _rank_expression(q: str):  # noqa: ANN202
    """完整编号 > 编号前缀 > 标题 > 摘要 > 正文；其余命中排最后。"""
    key = q.casefold()
    pattern = _contains(q)
    prefix = f"{escape_like(key)}%"
    return case(
        (KnowledgeEntry.code_key == key, 0),
        (KnowledgeEntry.code_key.like(prefix, escape=LIKE_ESCAPE), 1),
        (KnowledgeEntry.title.ilike(pattern, escape=LIKE_ESCAPE), 2),
        (KnowledgeEntry.summary.ilike(pattern, escape=LIKE_ESCAPE), 3),
        (KnowledgeEntry.body.ilike(pattern, escape=LIKE_ESCAPE), 4),
        else_=5,
    )


def _match_condition(q: str):  # noqa: ANN202
    pattern = _contains(q)
    key_pattern = f"%{escape_like(q.casefold())}%"
    return or_(
        KnowledgeEntry.code_key.like(key_pattern, escape=LIKE_ESCAPE),
        KnowledgeEntry.title.ilike(pattern, escape=LIKE_ESCAPE),
        KnowledgeEntry.summary.ilike(pattern, escape=LIKE_ESCAPE),
        KnowledgeEntry.body.ilike(pattern, escape=LIKE_ESCAPE),
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
        conditions.append(_match_condition(q))
    return conditions


def _cursor_condition(after: tuple[int, str, str]):  # noqa: ANN202
    _rank, code, entry_id = after
    return or_(
        KnowledgeEntry.code_key > code,
        and_(
            KnowledgeEntry.code_key == code,
            KnowledgeEntry.entry_id > entry_id,
        ),
    )


def _ranked_cursor_condition(rank_col, after: tuple[int, str, str]):  # noqa: ANN001, ANN202
    rank, code, entry_id = after
    return or_(
        rank_col > rank,
        and_(
            rank_col == rank,
            or_(
                KnowledgeEntry.code_key > code,
                and_(
                    KnowledgeEntry.code_key == code,
                    KnowledgeEntry.entry_id > entry_id,
                ),
            ),
        ),
    )


async def search_entries_page(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    kb_id: str | None = None,
    entry_type: str | None = None,
    q: str | None = None,
    include_superseded: bool = False,
    limit: int,
    after: tuple[int, str, str] | None = None,
) -> list[EntryRow]:
    rank_col = _rank_expression(q) if q else literal(0)
    statement = (
        select(KnowledgeEntry, KnowledgeBase, rank_col.label("rank"))
        .join(KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id)
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
        statement = statement.where(
            _ranked_cursor_condition(rank_col, after) if q else _cursor_condition(after)
        )
    order = [rank_col.asc()] if q else []
    statement = statement.order_by(
        *order, KnowledgeEntry.code_key.asc(), KnowledgeEntry.entry_id.asc()
    ).limit(limit)
    rows = await db.execute(statement)
    return [(row[0], row[1], int(row[2])) for row in rows.all()]


async def counts_by_type(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    kb_id: str | None = None,
    q: str | None = None,
    include_superseded: bool = False,
) -> dict[str, int]:
    """忽略 ``type`` 条件、共用其他条件一次聚合，与列表口径一致。"""
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
    rows = await db.execute(statement)
    return {row[0]: int(row[1]) for row in rows.all()}


async def list_conflict_rows(
    db: AsyncSession, *, scopes: Sequence[tuple[int, str]]
) -> list[tuple[int, str, str, KnowledgeBase]]:
    """按 ``(project_id, code_key)`` 集合一次取回，含已取代版本。"""
    if not scopes:
        return []
    grouped: dict[int, set[str]] = {}
    for project_id, code_key in scopes:
        grouped.setdefault(project_id, set()).add(code_key)
    conditions = [
        and_(
            KnowledgeBase.project_id == project_id,
            KnowledgeEntry.code_key.in_(sorted(code_keys)),
        )
        for project_id, code_keys in grouped.items()
    ]
    statement = (
        select(
            KnowledgeEntry.code_key,
            KnowledgeEntry.content_digest,
            KnowledgeBase,
        )
        .join(KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id)
        .where(or_(*conditions))
        .order_by(KnowledgeEntry.code_key.asc(), KnowledgeBase.version.desc())
    )
    rows = await db.execute(statement)
    return [
        (row[0], row[1], row[2].project_id, row[2]) for row in rows.all()
    ]


async def resolve_neighbor_entries(
    db: AsyncSession, *, project_id: int, code_keys: Sequence[str]
) -> dict[str, KnowledgeEntry]:
    """在同项目当前版本内按编号解析一跳邻居。"""
    if not code_keys:
        return {}
    statement = (
        select(KnowledgeEntry)
        .join(KnowledgeBase, KnowledgeEntry.kb_id == KnowledgeBase.kb_id)
        .where(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.current_flag == "1",
            KnowledgeEntry.code_key.in_(list(code_keys)),
        )
        .order_by(KnowledgeEntry.entry_id.asc())
    )
    rows = await db.scalars(statement)
    resolved: dict[str, KnowledgeEntry] = {}
    for entry in rows:
        resolved.setdefault(entry.code_key, entry)
    return resolved


async def list_bases_page(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    include_superseded: bool = False,
    limit: int,
    after: tuple[datetime, str] | None = None,
) -> list[BaseRow]:
    statement = select(KnowledgeBase, ProjectContext).join(
        ProjectContext, KnowledgeBase.project_id == ProjectContext.project_id
    )
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
    rows = await db.execute(statement)
    return [(row[0], row[1]) for row in rows.all()]


async def current_bases(
    db: AsyncSession, *, scopes: Sequence[tuple[int, str]]
) -> dict[tuple[int, str], KnowledgeBase]:
    if not scopes:
        return {}
    conditions = [
        and_(
            KnowledgeBase.project_id == project_id,
            KnowledgeBase.name_key == name_key,
        )
        for project_id, name_key in scopes
    ]
    statement = select(KnowledgeBase).where(
        KnowledgeBase.current_flag == "1", or_(*conditions)
    )
    rows = await db.scalars(statement)
    return {(row.project_id, row.name_key): row for row in rows}


__all__ = [
    "LIKE_ESCAPE",
    "counts_by_type",
    "current_bases",
    "escape_like",
    "list_bases_page",
    "list_conflict_rows",
    "resolve_neighbor_entries",
    "search_entries_page",
]
