"""边界输入校验：字段错误统一转成 DomainError。"""

from __future__ import annotations

from urllib.parse import urlsplit

from workbench.services.errors import DomainError

MAX_URL_LENGTH = 500


def _invalid(field: str, message: str) -> DomainError:
    return DomainError(
        "validation_error",
        "请求参数校验失败。",
        details=[{"field": field, "message": message}],
    )


def require_text(
    value: str | None, *, field: str, min_length: int = 1, max_length: int | None = None
) -> str:
    cleaned = (value or "").strip()
    if len(cleaned) < min_length:
        raise _invalid(field, f"长度必须为 {min_length}–{max_length or '不限'}")
    if max_length is not None and len(cleaned) > max_length:
        raise _invalid(field, f"长度必须为 {min_length}–{max_length}")
    return cleaned


def optional_text(
    value: str | None, *, field: str, max_length: int | None = None
) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if max_length is not None and len(cleaned) > max_length:
        raise _invalid(field, f"长度不能超过 {max_length}")
    return cleaned


def require_http_url(
    value: str, *, field: str, max_length: int = MAX_URL_LENGTH
) -> str:
    if len(value) > max_length:
        raise _invalid(field, f"长度不能超过 {max_length}")
    split = urlsplit(value)
    if split.scheme not in ("http", "https") or not split.netloc:
        raise _invalid(field, "必须是 http(s) 绝对地址")
    if split.username or split.password:
        raise _invalid(field, "地址不能包含用户名或口令")
    return value
