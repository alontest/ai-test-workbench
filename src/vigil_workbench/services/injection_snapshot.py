"""读取时按 kbId 左连接 knowledge_base，计算 kbDeleted。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession


async def existing_kb_id_set(db: AsyncSession) -> set[str] | None:
    """表不存在返回 None；存在则返回 kb_id 字符串集合。"""

    def _load(sync_session) -> set[str] | None:  # noqa: ANN001
        bind = sync_session.get_bind()
        inspector = inspect(bind)
        inspector.clear_cache()
        if not inspector.has_table("knowledge_base"):
            return None
        rows = sync_session.execute(text("SELECT kb_id FROM knowledge_base"))
        return {str(row[0]) for row in rows}

    return await db.run_sync(_load)


def with_kb_deleted(
    items: list[dict[str, Any]] | None, present: set[str] | None
) -> list[dict[str, Any]] | None:
    if items is None:
        return None
    annotated: list[dict[str, Any]] = []
    for item in items:
        cloned = dict(item)
        cloned["kbDeleted"] = present is None or str(cloned.get("kbId")) not in present
        annotated.append(cloned)
    return annotated
