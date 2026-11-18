"""路由级依赖：Origin / Referer 校验。"""

from __future__ import annotations

from urllib.parse import urlsplit

from fastapi import Request

from workbench.api.errors import ApiError

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _origin_of(value: str | None) -> str | None:
    if not value:
        return None
    split = urlsplit(value)
    if split.scheme and split.netloc:
        return f"{split.scheme}://{split.netloc}"
    return None


async def require_same_origin(request: Request) -> None:
    if request.method.upper() in SAFE_METHODS:
        return
    origin = _origin_of(request.headers.get("origin")) or _origin_of(
        request.headers.get("referer")
    )
    allowed = getattr(request.app.state, "settings", None)
    allowed_origins = allowed.public_origins if allowed is not None else ()
    if origin is None or origin not in allowed_origins:
        raise ApiError(403, "forbidden_origin", "请求来源不被允许。")
