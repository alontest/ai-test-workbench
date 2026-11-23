"""应用装配：路由、异常处理、requestId 与静态托管。"""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from workbench.api.errors import (
    ApiError,
    _request_header,
    error_body,
    register_error_handlers,
)
from workbench.api.v1.router import api_router
from workbench.config import Settings, get_settings
from workbench.core.entrances import get_entrance
from workbench.db.engine import Database, configure_database, create_engine_from_url
from workbench.services import auth
from workbench.services.knowledge import scan_orphan_dirs
from workbench.services.knowledge.registration import (
    install_injection_preparer,
    uninstall_injection_preparer,
)

logger = logging.getLogger(__name__)

WEB_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def create_app(
    *,
    settings: Settings | None = None,
    database: Database | None = None,
    ai_gateway=None,  # noqa: ANN001
) -> FastAPI:
    resolved_settings = settings or get_settings()
    owned_database: Database | None = None
    if database is None:
        owned_database = Database(
            create_engine_from_url(resolved_settings.resolved_database_url)
        )
        database = owned_database
    configure_database(database)

    @asynccontextmanager
    async def lifespan(app: FastAPI):  # noqa: ANN202
        install_injection_preparer(app)
        try:
            try:
                removed = await scan_orphan_dirs(sessionmaker=database.sessionmaker)
                if removed:
                    logger.info(
                        "knowledge-bases orphan dirs removed count=%s", removed
                    )
            except Exception:  # noqa: BLE001 - 清理失败不阻塞启动
                logger.warning("knowledge-bases orphan scan failed")
            yield
        finally:
            uninstall_injection_preparer()
            if owned_database is not None:
                await owned_database.dispose()

    app = FastAPI(title="Vigil · 鸮巡", lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.database = database
    if ai_gateway is not None:
        app.state.ai_gateway = ai_gateway

    @app.middleware("http")
    async def _auth_guard(request: Request, call_next):  # noqa: ANN001, ANN202
        path = request.url.path
        if (
            request.method == "OPTIONS"
            or path == "/api/v1/auth/login"
            or path == "/login"
            or path.startswith("/assets/")
            or path == "/favicon.ico"
        ):
            return await call_next(request)
        token = request.cookies.get("aw_session")
        session = await auth.authenticate(token)
        if session is not None:
            request.state.login_session = session
            request.state.auth_token = token
            return await call_next(request)
        if path.startswith("/api/"):
            request_id = getattr(request.state, "request_id", "")
            headers = {"X-Request-Id": request_id} if request_id else {}
            return JSONResponse(
                status_code=401,
                content={
                    "code": "unauthorized",
                    "message": "未登录或会话已过期。",
                    "details": [],
                    "requestId": request_id,
                },
                headers=headers,
            )
        target = path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(
            "/login?next=" + quote(target, safe=""), status_code=302
        )

    @app.middleware("http")
    async def _request_id(request: Request, call_next):  # noqa: ANN001, ANN202
        request.state.request_id = uuid.uuid4().hex[:12]
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response

    register_error_handlers(app)
    app.include_router(api_router)

    @app.get("/entrances/{key}", include_in_schema=False)
    async def _entrance_html(key: str):  # noqa: ANN202
        if get_entrance(key) is None:
            raise ApiError(
                400,
                "entrance_unknown",
                "未知入口。",
                [{"field": "key", "message": key}],
            )
        index = WEB_DIST / "index.html"
        if index.is_file():
            return FileResponse(index)
        raise ApiError(404, "not_found", "页面不存在。")

    if WEB_DIST.is_dir():
        _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    """SPA 兜底：只接未被任何路由匹配的 GET 请求。

    不能注册成 ``@app.get("/{full_path:path}")``——通配路由会参与匹配并
    抢占之后注册的具体路由（含测试动态添加的端点），把应有的 404 / 405 / 400
    全吞成 200。这里用 catch-all 路由挂在「路由表末尾」无法保证顺序，
    因此改为在异常处理层兜底：仅当没有任何路由匹配时返回 index.html。
    """
    index = WEB_DIST / "index.html"

    @app.exception_handler(StarletteHTTPException)
    async def _spa_fallback(request: Request, exc: StarletteHTTPException):  # noqa: ANN202
        # 非 404、或非 GET、或 API 路径 → 交回默认处理，保持原有错误体。
        if exc.status_code != 404 or request.method not in ("GET", "HEAD"):
            return await http_exception_handler(request, exc)

        full_path = request.url.path.lstrip("/")
        if full_path == "api" or full_path.startswith("api/"):
            # API 路径走统一错误体，不用 FastAPI 默认的 {"detail": ...}。
            return JSONResponse(
                status_code=404,
                content=error_body(request, "not_found", "接口不存在。"),
                headers=_request_header(request),
            )

        candidate = (WEB_DIST / full_path).resolve()
        if (
            full_path
            and candidate.is_relative_to(WEB_DIST.resolve())
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        if full_path.startswith("assets/") or full_path == "favicon.ico":
            return PlainTextResponse("Not Found", status_code=404)
        return FileResponse(index)

