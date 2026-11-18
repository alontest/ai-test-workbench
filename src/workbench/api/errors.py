"""统一错误体与异常处理。"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from workbench.services.errors import DomainError

logger = logging.getLogger(__name__)


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
    return {
        "code": code,
        "message": message,
        "details": list(details),
        "requestId": request_id_of(request),
    }


def _request_header(request: Request) -> dict[str, str]:
    request_id = request_id_of(request)
    return {"X-Request-Id": request_id} if request_id else {}


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
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(request, exc.code, exc.message, exc.details),
            headers=_request_header(request),
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

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error requestId=%s", request_id_of(request))
        return JSONResponse(
            status_code=500,
            content=error_body(request, "internal_error", "服务器内部错误。"),
            headers=_request_header(request),
        )
