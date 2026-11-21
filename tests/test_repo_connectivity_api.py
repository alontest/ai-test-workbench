"""连通性测试 API：成功、鉴权、网络、权限、未保存与超时预算。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.models import (
    RepoBinding,
    RepoFileReadRecord,
    RepoSyncRecord,
)
from workbench.repos.providers.github import GitHubProvider
from workbench.services.repos import connectivity_service

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
TIMEOUT_MESSAGE = "供应商请求超时。"


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


def repo_payload() -> dict[str, Any]:
    return {
        "full_name": "pay/checkout",
        "name": "checkout",
        "default_branch": "main",
        "html_url": "https://github.com/pay/checkout",
    }


def install_transport(
    monkeypatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    calls: list[httpx.Request] = []

    def factory(ref, tok, *, transport=None, timeout=10):  # noqa: ANN001, ANN202
        def wrapped(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        return GitHubProvider(
            ref, tok, transport=httpx.MockTransport(wrapped), timeout=timeout
        )

    monkeypatch.setattr(connectivity_service, "build_provider", factory)
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


async def create_binding(
    client, project_id: int, *, repo: str = "pay/checkout", tok: str | None = None
) -> tuple[str, str]:
    sentinel = tok or token()
    response = await client.post(
        f"/api/v1/projects/{project_id}/repo-bindings",
        json={
            "provider": "github",
            "repoIdentifier": repo,
            "token": sentinel,
        },
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["bindingId"], sentinel


async def binding_row(database, binding_id: str) -> RepoBinding:  # noqa: ANN001
    async with database.sessionmaker() as db:
        row = await db.get(RepoBinding, binding_id)
    assert row is not None
    return row


async def record_counts(database) -> tuple[int, int]:  # noqa: ANN001
    async with database.sessionmaker() as db:
        syncs = await db.scalar(
            select(func.count()).select_from(RepoSyncRecord)
        )
        reads = await db.scalar(
            select(func.count()).select_from(RepoFileReadRecord)
        )
    return syncs or 0, reads or 0


@pytest.mark.asyncio
async def test_tc208_saved_test_success_sets_connected(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    calls = install_transport(monkeypatch, lambda request: httpx.Response(200, json=repo_payload()))

    response = await client.post(
        f"{binding_url(binding_id)}/test-connection", headers=ORIGIN
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "success"
    assert body["message"] == "连接成功。"
    assert body["defaultBranch"] == "main"
    assert body["bindingStatus"] == "connected"
    assert body["latestCommitAt"] is None
    assert body["testedAt"].endswith("Z")
    assert sentinel not in response.text
    assert len(calls) == 1

    row = await binding_row(database, binding_id)
    assert row.status == "connected"
    assert row.last_verified_at is not None
    assert row.last_verify_result == "success"
    assert row.last_verify_message is None


@pytest.mark.asyncio
async def test_tc209_auth_failure_marks_token_invalid(api, monkeypatch, caplog) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(401, json={"message": "Bad credentials"}),
    )

    with caplog.at_level(logging.DEBUG, logger="workbench"):
        response = await client.post(
            f"{binding_url(binding_id)}/test-connection", headers=ORIGIN
        )

    assert response.status_code == 200, response.text
    assert response.json()["result"] == "auth-error"
    assert sentinel not in response.text
    assert sentinel not in caplog.text

    row = await binding_row(database, binding_id)
    assert row.status == "token_invalid"
    assert row.last_verify_result == "auth-error"


@pytest.mark.asyncio
async def test_tc210_network_and_timeout_do_not_change_status(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    install_transport(monkeypatch, lambda request: _raise(httpx.ConnectError("refused")))
    response = await client.post(
        f"{binding_url(binding_id)}/test-connection", headers=ORIGIN
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"] == "unreachable"

    install_transport(monkeypatch, lambda request: _raise(httpx.ReadTimeout("slow")))
    timed_out = await client.post(
        f"{binding_url(binding_id)}/test-connection", headers=ORIGIN
    )
    assert timed_out.status_code == 200, timed_out.text
    assert timed_out.json()["result"] == "unreachable"
    assert timed_out.json()["message"] == TIMEOUT_MESSAGE

    row = await binding_row(database, binding_id)
    assert row.status == "unverified"
    assert await record_counts(database) == (0, 0)


def _raise(exc: Exception):
    raise exc


@pytest.mark.asyncio
async def test_tc211_permission_denied_not_misclassified(api, monkeypatch) -> None:
    client, database, _, project_id = api
    denied_id, _ = await create_binding(
        client, project_id, repo="pay/permission-denied"
    )
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            403, json={"message": "Resource not accessible"}
        ),
    )

    denied = await client.post(
        f"{binding_url(denied_id)}/test-connection", headers=ORIGIN
    )
    assert denied.status_code == 200, denied.text
    assert denied.json()["result"] == "permission-denied"
    assert denied.json()["retryAfterAt"] is None
    assert (await binding_row(database, denied_id)).status == "token_invalid"

    limited_id, _ = await create_binding(
        client, project_id, repo="pay/rate-limited"
    )
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            403,
            headers={"Retry-After": "30"},
            json={"message": "slow down"},
        ),
    )
    limited = await client.post(
        f"{binding_url(limited_id)}/test-connection", headers=ORIGIN
    )
    assert limited.status_code == 200, limited.text
    assert limited.json()["result"] == "unreachable"
    assert limited.json()["retryAfterAt"] is not None

    not_found_id, _ = await create_binding(
        client, project_id, repo="pay/not-found"
    )
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(404, json={"message": "Not Found"}),
    )
    missing = await client.post(
        f"{binding_url(not_found_id)}/test-connection", headers=ORIGIN
    )
    assert missing.status_code == 200, missing.text
    assert missing.json()["result"] == "permission-denied"
    assert (await binding_row(database, not_found_id)).status == "token_invalid"

    throttled_id, _ = await create_binding(
        client, project_id, repo="pay/throttled"
    )
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(429, json={"message": "Too Many Requests"}),
    )
    throttled = await client.post(
        f"{binding_url(throttled_id)}/test-connection", headers=ORIGIN
    )
    assert throttled.status_code == 200, throttled.text
    assert throttled.json()["result"] == "unreachable"
    assert throttled.json()["message"] == "供应商限流，请稍后重试。"
    assert throttled.json()["retryAfterAt"] is None
    assert (await binding_row(database, throttled_id)).status == "unverified"


@pytest.mark.asyncio
async def test_tc212_unsaved_test_writes_nothing(api, monkeypatch) -> None:
    client, database, _, _ = api
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=repo_payload())
    )

    response = await client.post(
        "/api/v1/repo-bindings/test-connection",
        json={
            "provider": "github",
            "repoIdentifier": "pay/checkout",
            "token": token(),
        },
        headers=ORIGIN,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "success"
    assert body["bindingStatus"] is None
    assert len(calls) == 1

    async with database.sessionmaker() as db:
        assert await db.scalar(
            select(func.count()).select_from(RepoBinding)
        ) == 0
    assert await record_counts(database) == (0, 0)


@pytest.mark.asyncio
async def test_tc214_token_expiration_header_null_when_absent(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            headers={"GitHub-Authentication-Token-Expiration": "2027-01-01T00:00:00Z"},
            json=repo_payload(),
        ),
    )
    await client.post(f"{binding_url(binding_id)}/test-connection", headers=ORIGIN)
    with_expiry = await client.get(binding_url(binding_id))
    assert with_expiry.json()["tokenExpiresAt"] is not None

    install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=repo_payload())
    )
    await client.post(f"{binding_url(binding_id)}/test-connection", headers=ORIGIN)
    without_header = await client.get(binding_url(binding_id))
    assert without_header.json()["tokenExpiresAt"] is None

    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            headers={"GitHub-Authentication-Token-Expiration": "not-a-date"},
            json=repo_payload(),
        ),
    )
    await client.post(f"{binding_url(binding_id)}/test-connection", headers=ORIGIN)
    garbage = await client.get(binding_url(binding_id))
    assert garbage.json()["tokenExpiresAt"] is None


@pytest.mark.asyncio
async def test_tc215_connectivity_respects_ten_second_budget(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    class Hanging:
        token_expires_at = None

        def __init__(self, ref, tok, *, transport=None, timeout=10) -> None:  # noqa: ANN001
            pass

        async def get_repository(self, ref):  # noqa: ANN001, ANN201
            await asyncio.sleep(5)

        async def aclose(self) -> None:
            pass

    monkeypatch.setattr(
        connectivity_service,
        "build_provider",
        lambda ref, tok, *, transport=None, timeout=10: Hanging(ref, tok),
    )

    started = time.monotonic()
    result = await connectivity_service.test_saved(binding_id, timeout=0.05)
    elapsed = time.monotonic() - started

    assert result["result"] == "unreachable"
    assert result["message"] == TIMEOUT_MESSAGE
    assert elapsed < 2
    assert (await binding_row(database, binding_id)).status == "unverified"
    assert await record_counts(database) == (0, 0)
