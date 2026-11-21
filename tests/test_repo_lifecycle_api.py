"""解绑生命周期：状态守卫、幂等解绑、历史保留与重新绑定。用例名带 TC 编号。"""

from __future__ import annotations

import uuid
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.base import utcnow
from workbench.db.models import (
    RepoBinding,
    RepoFileReadRecord,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)
from workbench.repos.crypto import decrypt_token
from workbench.repos.providers.github import GitHubProvider
from workbench.services.repos import connectivity_service

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


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


async def tables(database) -> dict[str, int]:  # noqa: ANN001
    async with database.sessionmaker() as db:
        return {
            "bindings": await db.scalar(
                select(func.count()).select_from(RepoBinding)
            ),
            "snapshots": await db.scalar(
                select(func.count()).select_from(RepoMetadataSnapshot)
            ),
            "syncs": await db.scalar(
                select(func.count()).select_from(RepoSyncRecord)
            ),
            "reads": await db.scalar(
                select(func.count()).select_from(RepoFileReadRecord)
            ),
        }


@pytest.mark.asyncio
async def test_tc227_revoked_binding_blocks_provider_calls(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    calls: list[httpx.Request] = []

    def factory(ref, tok, *, transport=None, timeout=10):  # noqa: ANN001, ANN202
        calls.append(httpx.Request("GET", "https://api.github.com/repos/pay/checkout"))
        return GitHubProvider(
            ref, tok, transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})), timeout=timeout
        )

    monkeypatch.setattr(connectivity_service, "build_provider", factory)

    unbound = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert unbound.status_code == 200, unbound.text

    tested = await client.post(
        f"{binding_url(binding_id)}/test-connection", headers=ORIGIN
    )
    assert tested.status_code == 409
    assert tested.json()["code"] == "binding_revoked"

    patched = await client.patch(
        f"{binding_url(binding_id)}/token",
        json={"token": token()},
        headers=ORIGIN,
    )
    assert patched.status_code == 409
    assert patched.json()["code"] == "binding_revoked"
    assert calls == []


@pytest.mark.asyncio
async def test_tc242_unbind_clears_token_and_is_idempotent(api) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    response = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "revoked"
    assert body["tokenMasked"] == ""
    assert body["revokedAt"] is not None

    row = await binding_row(database, binding_id)
    assert row.active_flag is None
    assert row.token_ciphertext is None
    assert row.token_masked is None

    again = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert again.status_code == 200, again.text
    assert again.json()["revokedAt"] == body["revokedAt"]


@pytest.mark.asyncio
async def test_tc243_unbind_keeps_snapshots_and_history(api) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    now = utcnow()
    async with database.sessionmaker() as db:
        db.add(
            RepoMetadataSnapshot(
                snapshot_id=uuid4().hex,
                binding_id=binding_id,
                repo_id="pay/checkout",
                kind="repo",
                ref="main",
                payload={"defaultBranch": "main"},
                fetched_at=now,
            )
        )
        db.add(
            RepoSyncRecord(
                sync_id=uuid4().hex,
                binding_id=binding_id,
                started_at=now,
                finished_at=now,
                status="success",
            )
        )
        db.add(
            RepoFileReadRecord(
                read_id=uuid4().hex,
                binding_id=binding_id,
                repo_id="pay/checkout",
                ref="main",
                file_path="README.md",
                encoding="text",
                status="success",
                fetched_at=now,
            )
        )
        await db.commit()

    before = await tables(database)
    unbound = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert unbound.status_code == 200, unbound.text
    assert await tables(database) == before

    row = await binding_row(database, binding_id)
    assert row.status == "revoked"


@pytest.mark.asyncio
async def test_tc244_rebind_creates_new_binding_and_token(api) -> None:
    client, database, settings, project_id = api
    old_id, old_token = await create_binding(client, project_id)
    old_row = await binding_row(database, old_id)

    await client.post(f"{binding_url(old_id)}/unbind", headers=ORIGIN)

    new_token = token("new1")
    new_id, _ = await create_binding(client, project_id, tok=new_token)
    assert new_id != old_id

    new_row = await binding_row(database, new_id)
    assert new_row.token_ciphertext != old_row.token_ciphertext
    assert decrypt_token(
        new_row.token_ciphertext, key=settings.repo_token_key_bytes
    ) == new_token

    still_revoked = await binding_row(database, old_id)
    assert still_revoked.status == "revoked"
    async with database.sessionmaker() as db:
        assert await db.scalar(
            select(func.count())
            .select_from(RepoBinding)
            .where(RepoBinding.status == "revoked")
        ) == 1
