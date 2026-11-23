"""项目接口。用例名带 TC 编号。"""

from __future__ import annotations

import pytest

from helpers import build_client, make_app, seed_admin

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


@pytest.fixture
async def client(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as http:
        login = await http.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        yield http


@pytest.mark.asyncio
async def test_tc013_api_create_and_conflict(client) -> None:
    response = await client.post(
        "/api/v1/projects", json={"name": "支付中心"}, headers=ORIGIN
    )
    assert response.status_code == 201
    body = response.json()
    assert body["projectId"] > 0
    assert body["name"] == "支付中心"

    duplicate = await client.post(
        "/api/v1/projects", json={"name": " 支付中心 "}, headers=ORIGIN
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "project_name_duplicate"
    assert duplicate.json()["details"][0]["field"] == "name"

    listing = await client.get("/api/v1/projects")
    assert listing.status_code == 200
    payload = listing.json()
    assert set(payload) == {"items", "nextCursor"}
    assert len(payload["items"]) == 1


@pytest.mark.asyncio
async def test_tc014_api_patch(client) -> None:
    created = (
        await client.post("/api/v1/projects", json={"name": "支付中心"}, headers=ORIGIN)
    ).json()

    patched = await client.patch(
        f"/api/v1/projects/{created['projectId']}",
        json={"techStack": "FastAPI", "notes": None},
        headers=ORIGIN,
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["techStack"] == "FastAPI"
    assert body["notes"] is None
    assert body["updatedAt"] > created["updatedAt"]

    detail = await client.get(f"/api/v1/projects/{created['projectId']}")
    assert detail.json()["techStack"] == "FastAPI"

    missing = await client.get("/api/v1/projects/999999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "project_not_found"


@pytest.mark.asyncio
async def test_tc016_api_validation_fields(client) -> None:
    bad_name = await client.post(
        "/api/v1/projects", json={"name": "  "}, headers=ORIGIN
    )
    assert bad_name.status_code == 400
    assert bad_name.json()["details"][0]["field"] == "name"

    bad_url = await client.post(
        "/api/v1/projects",
        json={"name": "合法", "repoUrl": "ftp://example.com/repo"},
        headers=ORIGIN,
    )
    assert bad_url.status_code == 400
    assert bad_url.json()["details"][0]["field"] == "repoUrl"

    listing = await client.get("/api/v1/projects")
    assert listing.json()["items"] == []

    ok = await client.post(
        "/api/v1/projects",
        json={"name": "x" * 100, "repoUrl": "https://example.com/repo"},
        headers=ORIGIN,
    )
    assert ok.status_code == 201
