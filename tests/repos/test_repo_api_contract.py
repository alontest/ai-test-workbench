"""API 契约：15 个端点受会话保护、错误体结构与时间格式。用例名带 TC 编号。"""

from __future__ import annotations

import re
import uuid

import pytest
import pytest_asyncio

from helpers import build_client, make_app, seed_admin, seed_project

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")

ENDPOINTS = {
    ("GET", "/api/v1/projects/{project_id}/repo-bindings"),
    ("POST", "/api/v1/projects/{project_id}/repo-bindings"),
    ("GET", "/api/v1/repo-bindings/{binding_id}"),
    ("PATCH", "/api/v1/repo-bindings/{binding_id}/token"),
    ("POST", "/api/v1/repo-bindings/{binding_id}/test-connection"),
    ("POST", "/api/v1/repo-bindings/test-connection"),
    ("POST", "/api/v1/repo-bindings/{binding_id}/sync"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/sync-records"),
    ("POST", "/api/v1/repo-bindings/{binding_id}/unbind"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/repositories"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/branches"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/commits"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/tree"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/file"),
    ("GET", "/api/v1/repo-bindings/{binding_id}/baseline"),
}


@pytest_asyncio.fixture
async def app(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker)
    yield make_app(settings=settings, database=database), project_id


async def login(client) -> None:  # noqa: ANN001
    response = await client.post(
        "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
    )
    assert response.status_code == 200, response.text


def assert_error_body(body: dict[str, object], code: str) -> None:
    assert set(body) == {"code", "message", "details", "requestId"}
    assert body["code"] == code
    assert isinstance(body["message"], str) and body["message"]
    assert isinstance(body["details"], list)
    assert isinstance(body["requestId"], str)


@pytest.mark.asyncio
async def test_tc245_all_repo_endpoints_require_session(app) -> None:
    application, _ = app
    paths = application.openapi()["paths"]
    documented = {
        (method.upper(), path)
        for path, operations in paths.items()
        for method in operations
    }
    assert ENDPOINTS <= documented

    async with build_client(application) as client:
        probes = [
            ("GET", "/api/v1/projects/1/repo-bindings"),
            ("POST", "/api/v1/projects/1/repo-bindings"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}"),
            ("PATCH", f"/api/v1/repo-bindings/{'0' * 32}/token"),
            ("POST", f"/api/v1/repo-bindings/{'0' * 32}/test-connection"),
            ("POST", "/api/v1/repo-bindings/test-connection"),
            ("POST", f"/api/v1/repo-bindings/{'0' * 32}/sync"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/sync-records"),
            ("POST", f"/api/v1/repo-bindings/{'0' * 32}/unbind"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/repositories"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/branches"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/commits?ref=main"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/tree?ref=main"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/file?ref=main&path=a.txt"),
            ("GET", f"/api/v1/repo-bindings/{'0' * 32}/baseline"),
        ]
        for method, path in probes:
            response = await client.request(method, path, headers=ORIGIN)
            assert response.status_code == 401, (method, path, response.text)
            body = response.json()
            assert body["code"] == "unauthorized"
            # 不泄露资源存在性：未登录一律 401，不出现 404/409。
            assert body["details"] == []


@pytest.mark.asyncio
async def test_tc249_error_body_and_time_format(app) -> None:
    application, project_id = app
    async with build_client(application) as client:
        await login(client)
        created = await client.post(
            f"/api/v1/projects/{project_id}/repo-bindings",
            json={
                "provider": "github",
                "repoIdentifier": "pay/checkout",
                "token": "ghp_contract_token_1234",
            },
            headers=ORIGIN,
        )
        assert created.status_code == 201, created.text
        binding = created.json()
        assert RFC3339.match(binding["createdAt"])
        assert RFC3339.match(binding["updatedAt"])
        binding_id = binding["bindingId"]

        limited = await client.get(
            f"/api/v1/repo-bindings/{binding_id}/repositories?limit=0"
        )
        assert limited.status_code == 400, limited.text
        limited_body = limited.json()
        assert_error_body(limited_body, "validation_error")
        assert limited_body["details"][0]["field"].endswith("limit")

        invalid_path = await client.get(
            f"/api/v1/repo-bindings/{binding_id}/file"
            "?ref=main&path=../escape"
        )
        assert invalid_path.status_code == 400, invalid_path.text
        invalid_body = invalid_path.json()
        assert_error_body(invalid_body, "invalid_path")
        assert invalid_body["details"][0]["field"] == "path"

        missing = await client.get(
            f"/api/v1/repo-bindings/{uuid.uuid4().hex}/baseline"
        )
        assert missing.status_code == 404, missing.text
        assert_error_body(missing.json(), "binding_not_found")
