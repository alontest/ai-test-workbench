"""统一错误体与异常处理。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError

from vigil_workbench.services.errors import DomainError

logger = logging.getLogger(__name__)

MYSQL_CHECK_CONSTRAINT_VIOLATION = 3819
MYSQL_DUPLICATE_ENTRY = 1062
MYSQL_FOREIGN_KEY_VIOLATION = 1451
MYSQL_FOREIGN_KEY_MISSING = 1452

_DB_CHECK_MESSAGE = "请求参数违反数据约束。"
_DB_CONFLICT_MESSAGE = "资源已存在或状态冲突。"


def _dbapi_errno(exc: DBAPIError) -> int | None:
    args = getattr(getattr(exc, "orig", None), "args", ())
    return args[0] if args and isinstance(args[0], int) else None


def _orig_text(exc: DBAPIError) -> str:
    orig = getattr(exc, "orig", None)
    return str(orig if orig is not None else exc).lower()


def _map_dbapi_error(exc: DBAPIError) -> tuple[int, str, str] | None:
    """把双方言的约束违反映射为 4xx；未识别的数据库错误仍走 500。"""
    errno = _dbapi_errno(exc)
    text = _orig_text(exc)
    if errno == MYSQL_CHECK_CONSTRAINT_VIOLATION or "check constraint" in text:
        return 400, "validation_error", _DB_CHECK_MESSAGE
    if (
        errno == MYSQL_DUPLICATE_ENTRY
        or "unique constraint" in text
        or "duplicate entry" in text
    ):
        return 409, "conflict", _DB_CONFLICT_MESSAGE
    if (
        errno in (MYSQL_FOREIGN_KEY_VIOLATION, MYSQL_FOREIGN_KEY_MISSING)
        or "foreign key constraint" in text
    ):
        return 409, "conflict", _DB_CONFLICT_MESSAGE
    return None


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Sequence[Mapping[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = list(details or ())


def request_id_of(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def error_body(request: Request, code: str, message: str, details=()) -> dict[str, Any]:  # noqa: ANN001
    if isinstance(details, Mapping) and not isinstance(details, Sequence):
        serialized: list[Any] | dict[str, Any] = dict(details)
    else:
        serialized = list(details)
    return {
        "code": code,
        "message": message,
        "details": serialized,
        "requestId": request_id_of(request),
    }


def _request_header(request: Request) -> dict[str, str]:
    request_id = request_id_of(request)
    return {"X-Request-Id": request_id} if request_id else {}


async def _mark_session_failed(request: Request) -> None:
    """未捕获异常时 best-effort 标记会话失败（DB 不可用则跳过）。"""
    session_id = getattr(request.state, "session_id", None)
    if session_id is None:
        return
    try:
        from vigil_workbench.services.sessions import fail_session

        await fail_session(session_id)
    except Exception:  # noqa: BLE001 - 兜底路径不得再抛
        logger.warning(
            "failed to mark session failed requestId=%s", request_id_of(request)
        )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(request, exc.code, exc.message, exc.details),
            headers=_request_header(request),
        )

    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        headers = _request_header(request)
        headers.update(getattr(exc, "headers", {}) or {})
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(request, exc.code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = []
        for error in exc.errors():
            location = [str(part) for part in error.get("loc", ()) if part != "body"]
            details.append(
                {
                    "field": ".".join(location) or "body",
                    "message": error.get("msg", "invalid value"),
                }
            )
        return JSONResponse(
            status_code=400,
            content=error_body(
                request, "validation_error", "请求参数校验失败。", details
            ),
            headers=_request_header(request),
        )

    @app.exception_handler(DBAPIError)
    async def _dbapi_error(request: Request, exc: DBAPIError) -> JSONResponse:
        mapped = _map_dbapi_error(exc)
        if mapped is None:
            logger.error(
                "database error requestId=%s errno=%s",
                request_id_of(request),
                _dbapi_errno(exc),
            )
            return JSONResponse(
                status_code=500,
                content=error_body(request, "internal_error", "服务器内部错误。"),
                headers=_request_header(request),
            )
        status_code, code, message = mapped
        logger.warning(
            "database constraint violation requestId=%s code=%s",
            request_id_of(request),
            code,
        )
        return JSONResponse(
            status_code=status_code,
            content=error_body(request, code, message),
            headers=_request_header(request),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        await _mark_session_failed(request)
        logger.exception("unhandled error requestId=%s", request_id_of(request))
        return JSONResponse(
            status_code=500,
            content=error_body(request, "internal_error", "服务器内部错误。"),
            headers=_request_header(request),
        )
