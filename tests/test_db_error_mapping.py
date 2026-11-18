"""数据库异常到 API 错误体的映射（TC-071）。"""

from __future__ import annotations

import httpx
from sqlalchemy.exc import IntegrityError, OperationalError

from workbench.main import create_app

ORIGIN = "http://testserver"


class _DBAPIStub(Exception):
    """模拟驱动原始异常（asyncmy / sqlite3）的 args 结构。"""


def _mysql_check_error() -> OperationalError:
    return OperationalError(
        "INSERT INTO provider_config ...",
        {},
        _DBAPIStub(
            3819, "Check constraint 'ck_provider_config_protocol' is violated."
        ),
    )


def _mysql_duplicate_error() -> IntegrityError:
    return IntegrityError(
        "INSERT INTO project_context ...",
        {},
        _DBAPIStub(
            1062,
            "Duplicate entry '支付中心' for key 'uq_project_context_name_key'",
        ),
    )


def _mysql_foreign_key_error() -> IntegrityError:
    return IntegrityError(
        "DELETE FROM project_context ...",
        {},
        _DBAPIStub(
            1451,
            "Cannot delete or update a parent row: a foreign key constraint fails",
        ),
    )


def _sqlite_check_error() -> IntegrityError:
    return IntegrityError(
        "INSERT INTO provider_config ...",
        {},
        _DBAPIStub("CHECK constraint failed: ck_provider_config_protocol"),
    )


def _connection_lost_error() -> OperationalError:
    return OperationalError(
        "SELECT 1", {}, _DBAPIStub(2006, "MySQL server has gone away")
    )


def _build_app(settings, database):  # noqa: ANN001
    app = create_app(settings=settings, database=database)

    @app.get("/api/v1/_db_check")
    async def _db_check() -> None:
        raise _mysql_check_error()

    @app.get("/api/v1/_db_duplicate")
    async def _db_duplicate() -> None:
        raise _mysql_duplicate_error()

    @app.get("/api/v1/_db_foreign_key")
    async def _db_foreign_key() -> None:
        raise _mysql_foreign_key_error()

    @app.get("/api/v1/_db_sqlite_check")
    async def _db_sqlite_check() -> None:
        raise _sqlite_check_error()

    @app.get("/api/v1/_db_down")
    async def _db_down() -> None:
        raise _connection_lost_error()

    return app


async def _get(app, path: str) -> httpx.Response:  # noqa: ANN001
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url=ORIGIN) as client:
        return await client.get(path)


async def test_tc071_db_error_mapping_is_dialect_portable(settings, database) -> None:  # noqa: ANN001
    app = _build_app(settings, database)

    check = await _get(app, "/api/v1/_db_check")
    assert check.status_code == 400
    body = check.json()
    assert body["code"] == "validation_error"
    assert body["requestId"] == check.headers["X-Request-Id"]
    assert "ck_provider_config_protocol" not in body["message"]

    duplicate = await _get(app, "/api/v1/_db_duplicate")
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "conflict"

    foreign_key = await _get(app, "/api/v1/_db_foreign_key")
    assert foreign_key.status_code == 409
    assert foreign_key.json()["code"] == "conflict"

    sqlite_check = await _get(app, "/api/v1/_db_sqlite_check")
    assert sqlite_check.status_code == 400
    assert sqlite_check.json()["code"] == "validation_error"

    down = await _get(app, "/api/v1/_db_down")
    assert down.status_code == 500
    assert down.json()["code"] == "internal_error"
