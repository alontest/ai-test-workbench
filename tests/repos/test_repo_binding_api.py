"""仓库绑定 API：创建、校验、去重、令牌更新、分页与域名默认值。用例名带 TC 编号。"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import (
    RepoBinding,
    RepoFileReadRecord,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)
from vigil_workbench.repos.crypto import decrypt_token

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


def api_url(project_id: int) -> str:
    return f"/api/v1/projects/{project_id}/repo-bindings"


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


def payload(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "provider": "github",
        "repoIdentifier": "pay/checkout",
        "token": token(),
    }
    body.update(overrides)
    return body


@pytest_asyncio.fixture
async def api(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings=settings, database=database)
    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        yield client, database, settings


async def _binding_row(database, binding_id: str) -> RepoBinding:  # noqa: ANN001
    async with database.sessionmaker() as db:
        row = await db.get(RepoBinding, binding_id)
    assert row is not None
    return row


async def _binding_count(database) -> int:  # noqa: ANN001
    async with database.sessionmaker() as db:
        return await db.scalar(
            select(func.count()).select_from(RepoBinding)
        )


def _columns(row: RepoBinding) -> dict[str, object]:
    return {
        column.name: getattr(row, column.name)
        for column in RepoBinding.__table__.columns
    }


@pytest.mark.asyncio
async def test_tc201_create_binding_encrypts_token_and_returns_mask(
    api, caplog
) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    sentinel = token("wxyz")

    with caplog.at_level(logging.DEBUG, logger="vigil_workbench"):
        response = await client.post(
            api_url(project_id), json=payload(token=sentinel), headers=ORIGIN
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert len(body["bindingId"]) == 32
    assert body["projectId"] == project_id
    assert body["provider"] == "github"
    assert body["apiBaseUrl"] == "https://api.github.com"
    assert body["repoName"] == "pay/checkout"
    assert body["status"] == "unverified"
    assert body["tokenMasked"].startswith("ghp_")
    assert body["tokenMasked"].endswith(sentinel[-4:])
    assert body["createdAt"].endswith("Z")
    assert sentinel not in response.text
    assert "v1:" not in response.text

    row = await _binding_row(database, body["bindingId"])
    assert row.token_ciphertext is not None
    assert row.token_ciphertext.startswith("v1:")
    assert sentinel not in row.token_ciphertext
    assert decrypt_token(
        row.token_ciphertext, key=settings.repo_token_key_bytes
    ) == sentinel
    assert row.token_masked == body["tokenMasked"]
    assert sentinel not in caplog.text


@pytest.mark.asyncio
async def test_tc202_create_binding_rejects_invalid_fields(api) -> None:
    client, database, _ = api
    project_id = await seed_project(database.sessionmaker)
    url = api_url(project_id)

    missing = await client.post(
        url,
        json={"provider": "github", "repoIdentifier": "pay/checkout"},
        headers=ORIGIN,
    )
    assert missing.status_code == 400

    empty = await client.post(url, json=payload(token="   "), headers=ORIGIN)
    assert empty.status_code == 400
    assert empty.json()["code"] == "token_required"

    bad_provider = await client.post(
        url, json=payload(provider="gitlab"), headers=ORIGIN
    )
    assert bad_provider.status_code == 400
    assert bad_provider.json()["code"] == "invalid_provider"

    bad_identifier = await client.post(
        url, json=payload(repoIdentifier="not a repo"), headers=ORIGIN
    )
    assert bad_identifier.status_code == 400
    assert bad_identifier.json()["code"] == "invalid_repo_identifier"

    bad_origin = await client.post(
        url,
        json=payload(apiBaseUrl="http://api.github.com"),
        headers=ORIGIN,
    )
    assert bad_origin.status_code == 400
    assert bad_origin.json()["code"] == "invalid_api_base_url"

    missing_org = await client.post(
        url,
        json=payload(
            provider="yunxiao", repoIdentifier="group/repo", orgId=""
        ),
        headers=ORIGIN,
    )
    assert missing_org.status_code == 400
    assert missing_org.json()["code"] == "validation_error"
    assert missing_org.json()["details"][0]["field"] == "orgId"

    assert await _binding_count(database) == 0


@pytest.mark.asyncio
async def test_tc203_duplicate_binding_rejected_original_unchanged(api) -> None:
    client, database, _ = api
    project_id = await seed_project(database.sessionmaker)
    first_token = token("first")

    first = await client.post(
        api_url(project_id), json=payload(token=first_token), headers=ORIGIN
    )
    assert first.status_code == 201, first.text
    original = await _binding_row(database, first.json()["bindingId"])

    duplicate = await client.post(
        api_url(project_id), json=payload(token=token("second")), headers=ORIGIN
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "repo_binding_duplicate"
    assert duplicate.json()["details"][0]["field"] == "repoIdentifier"

    assert await _binding_count(database) == 1
    unchanged = await _binding_row(database, first.json()["bindingId"])
    assert unchanged.token_ciphertext == original.token_ciphertext
    assert unchanged.token_masked == original.token_masked


@pytest.mark.asyncio
async def test_tc204_update_token_only_replaces_token_and_mask(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    old_token = token("old1")

    created = await client.post(
        api_url(project_id), json=payload(token=old_token), headers=ORIGIN
    )
    assert created.status_code == 201, created.text
    binding_id = created.json()["bindingId"]
    before = await _binding_row(database, binding_id)

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

    new_token = token("new1")
    updated = await client.patch(
        f"{binding_url(binding_id)}/token",
        json={"token": new_token},
        headers=ORIGIN,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["bindingId"] == binding_id

    after = await _binding_row(database, binding_id)
    assert after.token_ciphertext != before.token_ciphertext
    assert after.token_masked != before.token_masked
    assert decrypt_token(
        after.token_ciphertext, key=settings.repo_token_key_bytes
    ) == new_token
    assert new_token not in updated.text

    ignored = {"token_ciphertext", "token_masked", "updated_at"}
    before_other = {k: v for k, v in _columns(before).items() if k not in ignored}
    after_other = {k: v for k, v in _columns(after).items() if k not in ignored}
    assert after_other == before_other

    async with database.sessionmaker() as db:
        assert await db.scalar(
            select(func.count()).select_from(RepoMetadataSnapshot)
        ) == 1
        assert await db.scalar(
            select(func.count()).select_from(RepoSyncRecord)
        ) == 1
        assert await db.scalar(
            select(func.count()).select_from(RepoFileReadRecord)
        ) == 1


@pytest.mark.asyncio
async def test_tc205_binding_list_paginates_without_hard_limit(api) -> None:
    client, database, _ = api
    project_id = await seed_project(database.sessionmaker)
    created: list[str] = []
    for index in range(6):
        response = await client.post(
            api_url(project_id),
            json=payload(repoIdentifier=f"pay/checkout-{index}"),
            headers=ORIGIN,
        )
        assert response.status_code == 201, response.text
        created.append(response.json()["bindingId"])

    seen: list[str] = []
    cursor = None
    while True:
        params: dict[str, object] = {"limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        page = await client.get(api_url(project_id), params=params)
        assert page.status_code == 200, page.text
        body = page.json()
        assert len(body["items"]) <= 2
        seen.extend(item["bindingId"] for item in body["items"])
        cursor = body["nextCursor"]
        if cursor is None:
            break

    assert len(seen) == 6
    assert len(set(seen)) == 6
    assert set(seen) == set(created)


@pytest.mark.asyncio
async def test_tc206_api_base_url_validation_and_provider_defaults(api) -> None:
    client, database, _ = api
    project_id = await seed_project(database.sessionmaker)
    url = api_url(project_id)

    github = await client.post(
        url,
        json={
            "provider": "github",
            "repoIdentifier": "pay/github-default",
            "token": token(),
        },
        headers=ORIGIN,
    )
    assert github.status_code == 201, github.text
    assert github.json()["apiBaseUrl"] == "https://api.github.com"
    assert github.json()["orgId"] is None

    yunxiao = await client.post(
        url,
        json={
            "provider": "yunxiao",
            "repoIdentifier": "group/yunxiao-default",
            "orgId": "org-1",
            "token": token(),
        },
        headers=ORIGIN,
    )
    assert yunxiao.status_code == 201, yunxiao.text
    assert yunxiao.json()["apiBaseUrl"] == "https://openapi-rdc.aliyuncs.com"

    custom = await client.post(
        url,
        json=payload(
            repoIdentifier="pay/custom", apiBaseUrl="https://github.example.com"
        ),
        headers=ORIGIN,
    )
    assert custom.status_code == 400
    assert custom.json()["code"] == "invalid_api_base_url"

    insecure = await client.post(
        url,
        json={
            "provider": "yunxiao",
            "repoIdentifier": "group/insecure",
            "orgId": "org-1",
            "apiBaseUrl": "http://openapi-rdc.aliyuncs.com",
            "token": token(),
        },
        headers=ORIGIN,
    )
    assert insecure.status_code == 400
    assert insecure.json()["code"] == "invalid_api_base_url"


@pytest.mark.asyncio
async def test_tc207_binding_not_found_and_project_not_found(api) -> None:
    client, database, _ = api
    project_id = await seed_project(database.sessionmaker)

    missing_binding = await client.get(binding_url(uuid.uuid4().hex))
    assert missing_binding.status_code == 404
    assert missing_binding.json()["code"] == "binding_not_found"

    missing_project = await client.get(api_url(project_id + 9999))
    assert missing_project.status_code == 404
    assert missing_project.json()["code"] == "project_not_found"
