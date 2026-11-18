"""响应序列化助手：RFC 3339 UTC 时间与分页。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def to_rfc3339(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat() + "Z"


def page_payload(items: list[Any], next_cursor: str | None) -> dict[str, Any]:
    return {"items": items, "nextCursor": next_cursor}
