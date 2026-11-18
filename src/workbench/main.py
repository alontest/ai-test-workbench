"""应用装配：路由、异常处理、requestId 与静态托管。"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from workbench.api.errors import register_error_handlers
from workbench.api.v1.router import api_router
from workbench.config import Settings, get_settings
from workbench.db.engine import Database, configure_database, create_engine_from_url
from workbench.services import auth

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
        yield
        if owned_database is not None:
            await owned_database.dispose()

    app = FastAPI(title="AI 测试工作台", lifespan=lifespan)
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

    if WEB_DIST.is_dir():
        _mount_spa(app)

    return app


def _mount_spa(app: FastAPI) -> None:
    index = WEB_DIST / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa(full_path: str):  # noqa: ANN202
        candidate = (WEB_DIST / full_path).resolve()
        if (
            full_path
            and candidate.is_relative_to(WEB_DIST.resolve())
            and candidate.is_file()
        ):
            return FileResponse(candidate)
        return FileResponse(index)

