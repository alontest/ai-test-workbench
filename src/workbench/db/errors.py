"""数据库错误分类助手：双方言一致的唯一键冲突判断。"""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError

MYSQL_DUPLICATE_ENTRY = 1062


def is_unique_violation(exc: DBAPIError) -> bool:
    args = getattr(getattr(exc, "orig", None), "args", ())
    if args and args[0] == MYSQL_DUPLICATE_ENTRY:
        return True
    text = str(getattr(exc, "orig", None) or exc).lower()
    return "unique constraint" in text or "duplicate entry" in text
