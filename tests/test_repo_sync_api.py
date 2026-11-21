"""同步 API：成功覆盖、失败保留、限流、仅元数据与记录分页。用例名带 TC 编号。"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.models import RepoBinding, RepoMetadataSnapshot, RepoSyncRecord
from workbench.repos.providers.github import GitHubProvider
from workbench.repos.types import Page, RepositorySummary
from workbench.services.repos import sync_service

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "repo" / "github_sync.json").read_text(
        encoding="utf-8"
    )
)
SERVER_ERROR_MESSAGE = "供应商服务异常。"


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


def sync_handler(
    fixture: dict[str, Any],
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/pay/checkout":
            return httpx.Response(200, json=fixture["repo"])
        if path == "/repos/pay/checkout/branches":
            pages = fixture["branch_pages"]
            page = int(request.url.params.get("page", "1"))
            headers = {}
            if page < len(pages):
                headers["Link"] = (
                    "<https://api.github.com/repos/pay/checkout/branches"
                    f"?page={page + 1}>; rel=\"next\""
                )
            return httpx.Response(200, json=pages[page - 1], headers=headers)
        if path == "/repos/pay/checkout/commits":
            return httpx.Response(200, json=fixture["commits"])
        raise AssertionError(f"未预期的路径：{path}")

    return handler


def install_transport(
    monkeypatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    calls: list[httpx.Request] = []

    def factory(ref, token_value, **kwargs):  # noqa: ANN001, ANN202
        def wrapped(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        return GitHubProvider(
            ref, token_value, transport=httpx.MockTransport(wrapped)
        )

    monkeypatch.setattr(sync_service, "build_provider", factory)
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
    client, project_id: int, *, repo: str = "pay/checkout"
) -> tuple[str, str]:
    sentinel = token()
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


async def snapshots(database, binding_id: str) -> list[RepoMetadataSnapshot]:  # noqa: ANN001
    async with database.sessionmaker() as db:
        rows = await db.scalars(
            select(RepoMetadataSnapshot).where(
                RepoMetadataSnapshot.binding_id == binding_id
            )
        )
        return list(rows)


async def sync_record_count(database, binding_id: str) -> int:  # noqa: ANN001
    async with database.sessionmaker() as db:
        return (
            await db.scalar(
                select(func.count())
                .select_from(RepoSyncRecord)
                .where(RepoSyncRecord.binding_id == binding_id)
            )
        ) or 0


@pytest.mark.asyncio
async def test_tc216_sync_success_replaces_snapshot_and_updates_summary(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    install_transport(monkeypatch, sync_handler(FIXTURE))

    response = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)

    assert response.status_code == 200, response.text
    body = response.json()
    record = body["record"]
    assert record["status"] == "success"
    assert record["repoCount"] == 1
    assert record["branchCount"] == 3
    assert record["commitCount"] == 2
    assert record["errorCategory"] is None
    assert record["durationMs"] is not None and record["durationMs"] >= 0
    assert record["finishedAt"] is not None
    assert body["binding"]["status"] == "connected"
    assert body["binding"]["lastSyncSuccessAt"] == record["finishedAt"]
    assert body["binding"]["baseline"]["ref"] == "main"
    assert body["binding"]["baseline"]["sha"] == FIXTURE["branch_pages"][0][0][
        "commit"
    ]["sha"]
    assert sentinel not in response.text

    rows = await snapshots(database, binding_id)
    kinds = [row.kind for row in rows]
    assert kinds.count("repo") == 1
    assert kinds.count("branch") == 3
    assert kinds.count("commit") == 2

    binding = await binding_row(database, binding_id)
    assert binding.last_sync_status == "success"
    assert binding.last_sync_success_at is not None
    assert binding.last_sync_duration_ms is not None
    assert binding.sync_started_at is None
    assert binding.default_branch == "main"


@pytest.mark.asyncio
async def test_tc219_sync_failure_preserves_old_snapshot_and_time(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    install_transport(monkeypatch, sync_handler(FIXTURE))
    first = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)
    assert first.status_code == 200, first.text

    before_rows = await snapshots(database, binding_id)
    before_ids = {row.snapshot_id for row in before_rows}
    before_time = (await binding_row(database, binding_id)).last_sync_success_at
    assert before_time is not None

    def failing(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/repos/pay/checkout":
            return httpx.Response(200, json=FIXTURE["repo"])
        if path == "/repos/pay/checkout/branches":
            page = request.url.params.get("page")
            if page == "2":
                return httpx.Response(500, json={"message": "boom"})
            return httpx.Response(
                200,
                json=FIXTURE["branch_pages"][0],
                headers={
                    "Link": '<https://api.github.com/repos/pay/checkout/branches?page=2>; rel="next"'
                },
            )
        raise AssertionError(f"未预期的路径：{path}")

    install_transport(monkeypatch, failing)
    second = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)

    assert second.status_code == 200, second.text
    record = second.json()["record"]
    assert record["status"] == "failed"
    assert record["errorCategory"] == "other"
    assert record["errorMessage"] == SERVER_ERROR_MESSAGE
    assert second.json()["binding"]["lastSyncSuccessAt"] == first.json()["record"][
        "finishedAt"
    ]

    after_rows = await snapshots(database, binding_id)
    assert {row.snapshot_id for row in after_rows} == before_ids
    assert len(after_rows) == len(before_rows)

    binding = await binding_row(database, binding_id)
    assert binding.last_sync_success_at == before_time
    assert binding.last_sync_status == "failed"
    assert binding.last_sync_error_category == "other"
    assert await sync_record_count(database, binding_id) == 2


@pytest.mark.asyncio
async def test_tc220_sync_rate_limit_reports_retry_after_without_retry(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    calls = install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            429,
            headers={"Retry-After": "30"},
            json={"message": "Too Many Requests"},
        ),
    )

    response = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)

    assert response.status_code == 200, response.text
    record = response.json()["record"]
    assert record["status"] == "failed"
    assert record["errorCategory"] == "rate_limit"
    assert record["retryAfterAt"] is not None
    assert len(calls) == 1
    assert sentinel not in response.text

    binding = await binding_row(database, binding_id)
    assert binding.status == "unverified"
    assert binding.last_sync_error_category == "rate_limit"
    assert binding.last_sync_retry_after is not None
    assert binding.last_sync_success_at is None


@pytest.mark.asyncio
async def test_tc221_sync_stores_metadata_only(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    commits = [
        {
            "sha": f"{index:040x}",
            "commit": {
                "message": f"commit {index}",
                "author": {
                    "name": "lin.t",
                    "date": f"2026-11-{20 - index % 19:02d}T00:00:00Z",
                },
            },
        }
        for index in range(150)
    ]
    fixture = {
        "repo": FIXTURE["repo"],
        "branch_pages": [FIXTURE["branch_pages"][0] + FIXTURE["branch_pages"][1]],
        "commits": commits,
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return sync_handler(fixture)(request)

    install_transport(monkeypatch, handler)
    response = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)

    assert response.status_code == 200, response.text
    assert response.json()["record"]["commitCount"] == 100

    rows = await snapshots(database, binding_id)
    kinds = {row.kind for row in rows}
    assert kinds == {"repo", "branch", "commit"}
    commit_rows = [row for row in rows if row.kind == "commit"]
    assert len(commit_rows) == 100
    assert all(
        set(row.payload) == {"sha", "shortSha", "title", "authorName", "committedAt"}
        for row in commit_rows
    )
    assert all("content" not in row.payload for row in rows)
    timestamps = [row.payload["committedAt"] for row in commit_rows]
    assert timestamps == sorted(timestamps, reverse=True)

    commit_request = next(
        request
        for request in requests
        if request.url.path.endswith("/commits")
    )
    assert commit_request.url.params["per_page"] == "100"


@pytest.mark.asyncio
async def test_tc222_sync_records_paginated_desc(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    empty = await client.get(
        f"{binding_url(binding_id)}/sync-records", headers=ORIGIN
    )
    assert empty.status_code == 200, empty.text
    assert empty.json() == {"items": [], "nextCursor": None}

    install_transport(monkeypatch, sync_handler(FIXTURE))
    for _ in range(3):
        synced = await client.post(
            f"{binding_url(binding_id)}/sync", headers=ORIGIN
        )
        assert synced.status_code == 200, synced.text

    first = await client.get(
        f"{binding_url(binding_id)}/sync-records?limit=2", headers=ORIGIN
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert len(body["items"]) == 2
    assert body["nextCursor"] is not None

    second = await client.get(
        f"{binding_url(binding_id)}/sync-records?limit=2&cursor={body['nextCursor']}",
        headers=ORIGIN,
    )
    assert second.status_code == 200, second.text
    tail = second.json()
    assert len(tail["items"]) == 1
    assert tail["nextCursor"] is None

    stamps = [
        item["startedAt"] for item in body["items"] + tail["items"]
    ]
    parsed = [
        datetime.fromisoformat(value.replace("Z", "+00:00")) for value in stamps
    ]
    assert parsed == sorted(parsed, reverse=True)
    assert {item["syncId"] for item in body["items"] + tail["items"]} == {
        item["syncId"]
        for item in (
            await client.get(
                f"{binding_url(binding_id)}/sync-records?limit=100",
                headers=ORIGIN,
            )
        ).json()["items"]
    }

    rejected = await client.get(
        f"{binding_url(binding_id)}/sync-records?cursor=not-a-cursor",
        headers=ORIGIN,
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "invalid_cursor"


class _GatedProvider:
    """阻塞在仓库详情，便于制造第二个并发请求。"""

    def __init__(self, entered: asyncio.Event, release: asyncio.Event) -> None:
        self.entered = entered
        self.release = release
        self.token_expires_at = None

    async def get_repository(self, repo):  # noqa: ANN001, ANN201
        self.entered.set()
        await self.release.wait()
        return RepositorySummary(
            repo_id="pay/checkout",
            full_name="pay/checkout",
            display_name="checkout",
            default_branch="main",
        )

    async def list_branches(self, repo, *, search, cursor, limit):  # noqa: ANN001, ANN201
        return Page(items=())

    async def list_commits(self, repo, *, ref, cursor, limit):  # noqa: ANN001, ANN201
        return Page(items=())

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_tc217_concurrent_sync_requests_return_409_single_record(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)

    entered = asyncio.Event()
    release = asyncio.Event()
    gated = _GatedProvider(entered, release)

    def factory(ref, token_value, **kwargs):  # noqa: ANN001, ANN202
        return gated

    monkeypatch.setattr(sync_service, "build_provider", factory)

    first = asyncio.create_task(
        client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)
    )
    await asyncio.wait_for(entered.wait(), timeout=2)

    second = await client.post(f"{binding_url(binding_id)}/sync", headers=ORIGIN)
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "sync_in_progress"

    release.set()
    finished = await first
    assert finished.status_code == 200, finished.text
    assert finished.json()["record"]["status"] == "success"
    assert await sync_record_count(database, binding_id) == 1
