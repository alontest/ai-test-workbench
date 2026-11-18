"""应用骨架、错误体、游标与 Origin 校验。用例名带 TC 编号。"""

from __future__ import annotations

import httpx
import pytest
from fastapi import Depends
from pydantic import BaseModel, Field

from workbench.api.deps import require_same_origin
from workbench.api.errors import ApiError, request_id_of
from workbench.api.pagination import decode_cursor, encode_cursor
from workbench.main import create_app


class _Payload(BaseModel):
    name: str = Field(min_length=2)


def _build_app(settings, database):
    app = create_app(settings=settings, database=database)

    @app.get("/api/v1/_boom")
    async def boom():  # noqa: ANN202
        raise RuntimeError("boom")

    @app.get("/api/v1/_missing")
    async def missing():  # noqa: ANN202
        raise ApiError(404, "session_not_found", "会话不存在。")

    @app.post("/api/v1/_validate")
    async def validate(payload: _Payload):  # noqa: ANN202
        return {"ok": payload.name}

    @app.post("/api/v1/_origin")
    async def origin(_=Depends(require_same_origin)):  # noqa: ANN001
        return {"ok": True}

    return app


@pytest.mark.asyncio
async def test_tc060_error_envelope_and_cursor(settings, database) -> None:
    app = _build_app(settings, database)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/_missing")
        assert response.status_code == 404
        body = response.json()
        assert set(body) == {"code", "message", "details", "requestId"}
        assert body["code"] == "session_not_found"
        assert body["details"] == []
        assert body["requestId"]

        response = await client.get("/api/v1/_boom")
        assert response.status_code == 500
        body = response.json()
        assert body["code"] == "internal_error"
        assert "boom" not in body["message"]
        assert response.headers["X-Request-Id"] == body["requestId"]

        response = await client.post("/api/v1/_validate", json={"name": "x"})
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "validation_error"
        assert body["details"][0]["field"] == "name"

    cursor = encode_cursor({"updated_at": "2026-11-18T02:30:00Z", "session_id": 9})
    assert decode_cursor(cursor) == {
        "updated_at": "2026-11-18T02:30:00Z",
        "session_id": 9,
    }
    with pytest.raises(ApiError) as err:
        decode_cursor("not-a-cursor!!")
    assert err.value.code == "validation_error"
    assert err.value.status_code == 400


@pytest.mark.asyncio
async def test_tc061_origin_check_rejects_cross_site(settings, database) -> None:
    app = _build_app(settings, database)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/_origin", headers={"Origin": "https://evil.example"}
        )
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden_origin"

        response = await client.post("/api/v1/_origin")
        assert response.status_code == 403

        response = await client.post(
            "/api/v1/_origin", headers={"Origin": "http://testserver"}
        )
        assert response.status_code == 200
        assert response.json() == {"ok": True}

        response = await client.post(
            "/api/v1/_origin", headers={"Referer": "http://testserver/sessions"}
        )
        assert response.status_code == 200

        response = await client.get("/api/v1/_origin")
        assert response.status_code == 405
