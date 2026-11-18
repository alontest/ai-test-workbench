"""认证接口：登录、登出与会话校验。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from workbench.api.deps import require_same_origin
from workbench.api.serialization import to_rfc3339
from workbench.api.schemas.auth import LoginRequest
from workbench.core.constants import LOGIN_IDLE_TIMEOUT
from workbench.services import auth

SESSION_COOKIE = "aw_session"

router = APIRouter(
    prefix="/auth", tags=["auth"], dependencies=[Depends(require_same_origin)]
)


def safe_next_path(value: str | None) -> str:
    """只接受站内绝对路径，其余回退首页（开放重定向防护）。"""
    if not value or "\r" in value or "\n" in value:
        return "/"
    if not value.startswith("/") or value.startswith("//") or value.startswith("/\\"):
        return "/"
    if value.lower().startswith("/%2f"):
        return "/"
    return value


def _cookie_secure(request: Request) -> bool:
    settings = request.app.state.settings
    if settings.cookie_secure == "true":
        return True
    if settings.cookie_secure == "false":
        return False
    scheme = request.url.scheme
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-proto", "")
        if forwarded:
            scheme = forwarded.split(",")[0].strip()
    return scheme == "https"


def _source_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/login")
async def login(payload: LoginRequest, request: Request) -> JSONResponse:
    token, _ = await auth.login(payload.password, _source_ip(request))
    response = JSONResponse({"authenticated": True})
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        path="/",
        secure=_cookie_secure(request),
    )
    return response


@router.post("/logout", status_code=204)
async def logout(request: Request) -> Response:
    token = request.cookies.get(SESSION_COOKIE)
    revoked = await auth.logout(token)
    if not revoked:
        from workbench.api.errors import ApiError

        raise ApiError(401, "unauthorized", "未登录或会话已过期。")
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@router.get("/session")
async def session_state(request: Request) -> dict[str, object]:
    row = request.state.login_session
    return {
        "authenticated": True,
        "lastSeenAt": to_rfc3339(row.last_seen_at),
        "idleExpiresAt": to_rfc3339(row.last_seen_at + LOGIN_IDLE_TIMEOUT),
    }
