"""安全哨兵：令牌与文件正文不进入响应、错误体、日志或审计记录。用例名带 TC 编号。"""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any, Callable
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from helpers import build_client, make_app, seed_admin, seed_project
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import RepoBinding, RepoFileReadRecord, RepoMetadataSnapshot
from vigil_workbench.repos.providers.github import GitHubProvider
from vigil_workbench.services.repos import live_access
from sqlalchemy import select

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
CONTENT_SENTINEL = "BODY_SENTINEL_7f3c9a1b"
TOKEN_SENTINEL_PREFIX = "ghp_RISENTINEL_"


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token() -> str:
    return f"{TOKEN_SENTINEL_PREFIX}{uuid.uuid4().hex}_abcd"


def install_transport(
    monkeypatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    calls: list[httpx.Request] = []

    def factory(ref, token_value):  # noqa: ANN001, ANN202
        def wrapped(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        return GitHubProvider(ref, token_value, transport=httpx.MockTransport(wrapped))

    monkeypatch.setattr(live_access, "build_provider", factory)
    return calls


@pytest_asyncio.fixture
async def api(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings=settings, database=database)
    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        project_id = await seed_project(database.sessionmaker)
        yield client, database, settings, project_id


async def create_binding(client, project_id: int) -> tuple[str, str]:
    sentinel = token()
    response = await client.post(
        f"/api/v1/projects/{project_id}/repo-bindings",
        json={"provider": "github", "repoIdentifier": "pay/checkout", "token": sentinel},
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["bindingId"], sentinel


async def seed_synced(database, binding_id: str) -> None:  # noqa: ANN001
    fetched_at = utcnow()
    async with database.sessionmaker() as db:
        row = await db.get(RepoBinding, binding_id)
        assert row is not None
        row.last_sync_success_at = fetched_at
        row.default_branch = "main"
        row.status = "connected"
        db.add(
            RepoMetadataSnapshot(
                snapshot_id=uuid4().hex,
                binding_id=binding_id,
                repo_id="pay/checkout",
                kind="repo",
                ref="main",
                payload={"repoId": "pay/checkout", "fullName": "pay/checkout"},
                fetched_at=fetched_at,
            )
        )
        await db.commit()


def blob(raw: bytes, *, size: int | None = None) -> dict[str, Any]:
    return {
        "name": "main.py",
        "path": "src/main.py",
        "size": len(raw) if size is None else size,
        "encoding": "base64",
        "content": base64.b64encode(raw).decode(),
    }


def browse_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/user/repos":
        return httpx.Response(
            200,
            json=[
                {
                    "full_name": "pay/checkout",
                    "name": "checkout",
                    "default_branch": "main",
                }
            ],
        )
    if path.endswith("/branches"):
        return httpx.Response(
            200, json=[{"name": "main", "commit": {"sha": "a" * 40}}]
        )
    if path.endswith("/commits"):
        return httpx.Response(
            200,
            json=[
                {
                    "sha": "a" * 40,
                    "commit": {
                        "message": "init",
                        "author": {"name": "lin.t", "date": "2026-01-01T00:00:00Z"},
                    },
                }
            ],
        )
    if path.endswith("/contents/src"):
        return httpx.Response(
            200,
            json=[{"name": "main.py", "path": "src/main.py", "type": "file", "size": 4}],
        )
    if path.endswith("/contents/src/main.py"):
        return httpx.Response(200, json=blob(CONTENT_SENTINEL.encode()))
    raise AssertionError(f"未预期的路径：{path}")


async def db_text(database) -> str:  # noqa: ANN001
    async with database.sessionmaker() as db:
        bindings = list(await db.scalars(select(RepoBinding)))
        reads = list(await db.scalars(select(RepoFileReadRecord)))
    return repr(
        [
            {key: value for key, value in row.__dict__.items() if not key.startswith("_")}
            for row in bindings + reads
        ]
    )


@pytest.mark.asyncio
async def test_tc246_token_never_in_logs_errors_or_records(
    api, monkeypatch, caplog
) -> None:
    caplog.set_level(logging.INFO)
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    await seed_synced(database, binding_id)
    calls = install_transport(monkeypatch, browse_handler)

    responses = [
        await client.get(f"{binding_url(binding_id)}/repositories"),
        await client.get(f"{binding_url(binding_id)}/branches"),
        await client.get(f"{binding_url(binding_id)}/commits?ref=main"),
        await client.get(f"{binding_url(binding_id)}/tree?ref=main&path=src"),
        await client.get(f"{binding_url(binding_id)}/file?ref=main&path=src/main.py"),
        await client.get(f"{binding_url(binding_id)}/baseline"),
    ]
    for response in responses:
        assert response.status_code == 200, response.text
        assert sentinel not in response.text

    assert calls
    assert all(call.method == "GET" for call in calls)
    assert all(call.headers["authorization"] == f"Bearer {sentinel}" for call in calls)
    assert all(sentinel not in str(call.url) for call in calls)

    # 失败路径同样不泄露：401 只返回固定码与分类字段。
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(401, json={"message": "Bad credentials"}),
    )
    failed = await client.get(f"{binding_url(binding_id)}/repositories")
    assert failed.status_code == 502
    assert sentinel not in failed.text
    assert "Bad credentials" not in failed.text

    assert sentinel not in caplog.text
    assert sentinel not in await db_text(database)


@pytest.mark.asyncio
async def test_tc241_file_content_never_in_logs_or_records(
    api, monkeypatch, caplog
) -> None:
    caplog.set_level(logging.INFO)
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    install_transport(monkeypatch, browse_handler)

    success = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/main.py"
    )
    assert success.status_code == 200, success.text
    assert success.json()["content"] == CONTENT_SENTINEL

    # 二进制拒绝：正文哨兵不能出现在错误体、日志或记录里。
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, json=blob(b"\x00" + CONTENT_SENTINEL.encode())
        ),
    )
    binary = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/blob.bin"
    )
    assert binary.status_code == 415
    assert binary.json()["code"] == "repo_file_binary"
    assert CONTENT_SENTINEL not in binary.text

    # 非 UTF-8 拒绝。
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200, json=blob(b"\xff\xfe" + CONTENT_SENTINEL.encode())
        ),
    )
    not_utf8 = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/latin1.txt"
    )
    assert not_utf8.status_code == 422
    assert not_utf8.json()["code"] == "repo_file_not_utf8"
    assert CONTENT_SENTINEL not in not_utf8.text

    # 超限拒绝：供应商不返回正文，错误体只含大小。
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={
                "name": "big.bin",
                "path": "big.bin",
                "size": 1_048_577,
                "encoding": "none",
                "content": "",
            },
        ),
    )
    too_large = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=big.bin"
    )
    assert too_large.status_code == 413
    assert too_large.json()["code"] == "repo_file_too_large"

    assert CONTENT_SENTINEL not in caplog.text
    assert CONTENT_SENTINEL not in await db_text(database)
    assert sentinel not in caplog.text
