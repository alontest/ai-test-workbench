"""浏览 API：实时仓库/分支/提交/目录树、未同步空态、游标与跨域基线。用例名带 TC 编号。"""

from __future__ import annotations

import re
import uuid
from typing import Any, Callable
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.base import utcnow
from workbench.db.models import RepoBinding, RepoMetadataSnapshot
from workbench.repos.providers.github import GitHubProvider
from workbench.services.repos import live_access

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


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


async def create_binding(
    client, project_id: int, *, repo: str = "pay/checkout"
) -> tuple[str, str]:
    sentinel = token()
    response = await client.post(
        f"/api/v1/projects/{project_id}/repo-bindings",
        json={"provider": "github", "repoIdentifier": repo, "token": sentinel},
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["bindingId"], sentinel


async def mark_synced(database, binding_id: str) -> None:  # noqa: ANN001
    async with database.sessionmaker() as db:
        row = await db.get(RepoBinding, binding_id)
        assert row is not None
        row.last_sync_success_at = utcnow()
        row.last_sync_status = "success"
        row.default_branch = "main"
        row.status = "connected"
        await db.commit()


async def binding_row(database, binding_id: str) -> RepoBinding:  # noqa: ANN001
    async with database.sessionmaker() as db:
        row = await db.get(RepoBinding, binding_id)
    assert row is not None
    return row


def repo_item(full_name: str = "pay/checkout", name: str = "checkout") -> dict[str, Any]:
    return {
        "full_name": full_name,
        "name": name,
        "default_branch": "main",
        "html_url": f"https://github.com/{full_name}",
    }


def commit_item(sha_char: str, title: str, date: str) -> dict[str, Any]:
    return {
        "sha": sha_char * 40,
        "commit": {
            "message": title,
            "author": {"name": "lin.t", "date": date},
        },
    }


@pytest.mark.asyncio
async def test_tc224_repositories_live_search_and_default(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/search/repositories":
            return httpx.Response(
                200,
                json={"items": [repo_item()], "total_count": 1},
            )
        return httpx.Response(
            200,
            json=[repo_item()],
            headers={
                "Link": '<https://api.github.com/user/repos?page=2>; rel="next"'
            },
        )

    calls = install_transport(monkeypatch, handler)

    searched = await client.get(
        f"{binding_url(binding_id)}/repositories?search=pay&limit=1"
    )
    assert searched.status_code == 200, searched.text
    body = searched.json()
    assert body["metadataSynced"] is True
    assert body["live"] is True
    assert body["guide"] is None
    assert body["total"] == 1
    assert body["items"][0]["repoId"] == "pay/checkout"
    assert body["items"][0]["webUrl"] == "https://github.com/pay/checkout"
    assert body["nextCursor"] is None

    listed = await client.get(f"{binding_url(binding_id)}/repositories?limit=1")
    assert listed.status_code == 200, listed.text
    listed_body = listed.json()
    assert [item["fullName"] for item in listed_body["items"]] == ["pay/checkout"]
    assert listed_body["nextCursor"] is not None

    assert calls[0].url.path == "/search/repositories"
    assert calls[0].url.params["q"] == "pay"
    assert calls[0].url.params["per_page"] == "1"
    assert all(call.method == "GET" for call in calls)
    assert calls[0].headers["authorization"] == f"Bearer {sentinel}"
    assert sentinel not in searched.text + listed.text


@pytest.mark.asyncio
async def test_tc225_branches_live_pagination_and_default_branch(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/branches"):
            page = request.url.params.get("page", "1")
            if page == "1":
                return httpx.Response(
                    200,
                    json=[
                        {"name": "main", "commit": {"sha": "a" * 40}},
                        {"name": "dev", "commit": {"sha": "b" * 40}},
                    ],
                    headers={
                        "Link": '<https://api.github.com/repos/pay/checkout/branches?page=2>; rel="next"'
                    },
                )
            return httpx.Response(
                200, json=[{"name": "release", "commit": {"sha": "c" * 40}}]
            )
        if path.endswith("/commits"):
            return httpx.Response(200, json=[commit_item("d", "dev only", "2026-01-01T00:00:00Z")])
        raise AssertionError(f"未预期的路径：{path}")

    calls = install_transport(monkeypatch, handler)

    first = await client.get(f"{binding_url(binding_id)}/branches?limit=2")
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert [item["name"] for item in first_body["items"]] == ["main", "dev"]
    assert first_body["items"][0]["isDefault"] is True
    assert first_body["items"][1]["isDefault"] is False
    assert first_body["nextCursor"] is not None

    second = await client.get(
        f"{binding_url(binding_id)}/branches?limit=2&cursor={first_body['nextCursor']}"
    )
    assert second.status_code == 200, second.text
    assert [item["name"] for item in second.json()["items"]] == ["release"]
    assert second.json()["nextCursor"] is None

    commits = await client.get(f"{binding_url(binding_id)}/commits?ref=dev")
    assert commits.status_code == 200, commits.text
    assert commits.json()["items"][0]["sha"] == "d" * 40
    commit_request = next(call for call in calls if call.url.path.endswith("/commits"))
    assert commit_request.url.params["sha"] == "dev"

    other = await client.get(
        f"{binding_url(binding_id)}/branches?repoId=pay/ledger"
    )
    assert other.status_code == 200, other.text
    other_request = calls[-1]
    assert other_request.url.path == "/repos/pay/ledger/branches"

    invalid = await client.get(
        f"{binding_url(binding_id)}/branches?repoId=not-a-repo"
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "invalid_repo_identifier"


@pytest.mark.asyncio
async def test_tc226_unsynced_browse_returns_empty_state(
    api, monkeypatch
) -> None:
    client, _, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(500, json={"message": "boom"})
    )

    urls = (
        f"{binding_url(binding_id)}/repositories",
        f"{binding_url(binding_id)}/branches",
        f"{binding_url(binding_id)}/commits?ref=main",
        f"{binding_url(binding_id)}/tree?ref=main&path=src",
    )
    for url in urls:
        response = await client.get(url)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["metadataSynced"] is False
        assert body["live"] is False
        assert body["items"] == []
        assert body["nextCursor"] is None
        assert body["guide"] == "sync_first"
    tree = (await client.get(urls[3])).json()
    assert tree["truncated"] is False
    assert tree["hasMore"] is False
    assert tree["path"] == "src"
    assert tree["ref"] == "main"
    assert calls == []


@pytest.mark.asyncio
async def test_tc227_revoked_browse_endpoints_return_409_without_calls(
    api, monkeypatch
) -> None:
    client, _, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    unbound = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert unbound.status_code == 200, unbound.text
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=[])
    )

    for url in (
        f"{binding_url(binding_id)}/repositories",
        f"{binding_url(binding_id)}/branches",
        f"{binding_url(binding_id)}/commits?ref=main",
        f"{binding_url(binding_id)}/tree?ref=main",
    ):
        response = await client.get(url)
        assert response.status_code == 409, response.text
        assert response.json()["code"] == "binding_revoked"
    assert calls == []


@pytest.mark.asyncio
async def test_tc228_token_invalid_live_502_and_baseline_still_readable(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    await mark_synced(database, binding_id)
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(401, json={"message": "Bad credentials"})
    )

    response = await client.get(f"{binding_url(binding_id)}/repositories")
    assert response.status_code == 502, response.text
    body = response.json()
    assert body["code"] == "provider_auth_failed"
    assert body["details"][0]["category"] == "auth"
    assert sentinel not in response.text
    assert len(calls) == 1

    row = await binding_row(database, binding_id)
    assert row.status == "token_invalid"

    baseline = await client.get(f"{binding_url(binding_id)}/baseline")
    assert baseline.status_code == 200, baseline.text
    payload = baseline.json()
    assert payload["status"] == "token_invalid"
    assert payload["revoked"] is False
    assert payload["lastSyncSuccessAt"] is not None
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_tc229_commits_live_desc_with_short_sha(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("sha") == "empty":
            return httpx.Response(200, json=[])
        return httpx.Response(
            200,
            json=[
                commit_item("b", "older", "2026-01-01T00:00:00Z"),
                commit_item("c", "newest", "2026-03-01T00:00:00Z"),
                commit_item("a", "middle", "2026-02-01T00:00:00Z"),
            ],
        )

    install_transport(monkeypatch, handler)

    page = await client.get(f"{binding_url(binding_id)}/commits?ref=main")
    assert page.status_code == 200, page.text
    items = page.json()["items"]
    assert [item["title"] for item in items] == ["newest", "middle", "older"]
    assert all(len(item["shortSha"]) == 7 for item in items)
    assert all(item["authorName"] == "lin.t" for item in items)
    assert all(RFC3339.match(item["committedAt"]) for item in items)

    empty = await client.get(f"{binding_url(binding_id)}/commits?ref=empty")
    assert empty.status_code == 200, empty.text
    assert empty.json()["items"] == []


@pytest.mark.asyncio
async def test_tc230_tree_lazy_pages_and_has_more(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    entries = [
        {"name": "main.py", "path": "src/main.py", "type": "file", "size": 12},
        {"name": "api", "path": "src/api", "type": "dir", "size": 0},
        {"name": "pkg", "path": "src/pkg", "type": "dir"},
        {"name": "b.py", "path": "src/b.py", "type": "file", "size": 7},
        {"name": "c.py", "path": "src/c.py", "type": "file", "size": 8},
    ]
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=entries)

    install_transport(monkeypatch, handler)

    first = await client.get(
        f"{binding_url(binding_id)}/tree?ref=main&path=src&limit=2"
    )
    assert first.status_code == 200, first.text
    body = first.json()
    assert [item["name"] for item in body["items"]] == ["main.py", "api"]
    assert body["items"][0]["type"] == "file"
    assert body["items"][0]["sizeBytes"] == 12
    assert body["items"][1]["type"] == "dir"
    assert body["items"][1]["sizeBytes"] is None
    assert body["hasMore"] is True
    assert body["truncated"] is False
    assert body["nextCursor"] is not None
    assert body["path"] == "src"
    assert body["ref"] == "main"
    assert body["total"] == 5

    second = await client.get(
        f"{binding_url(binding_id)}/tree?ref=main&path=src&limit=2"
        f"&cursor={body['nextCursor']}"
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert [item["name"] for item in second_body["items"]] == ["pkg", "b.py"]

    third = await client.get(
        f"{binding_url(binding_id)}/tree?ref=main&path=src&limit=2"
        f"&cursor={second_body['nextCursor']}"
    )
    assert third.status_code == 200, third.text
    third_body = third.json()
    assert [item["name"] for item in third_body["items"]] == ["c.py"]
    assert third_body["hasMore"] is False
    assert third_body["nextCursor"] is None
    assert all(call.url.path.endswith("/contents/src") for call in requests)
    assert all(call.url.params["ref"] == "main" for call in requests)


@pytest.mark.asyncio
async def test_tc231_tree_truncated_not_reported_as_complete(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    full = [
        {"name": f"f{i}.txt", "path": f"f{i}.txt", "type": "file", "size": 1}
        for i in range(1000)
    ]
    install_transport(monkeypatch, lambda request: httpx.Response(200, json=full))

    first = await client.get(f"{binding_url(binding_id)}/tree?ref=main&limit=100")
    assert first.status_code == 200, first.text
    body = first.json()
    assert len(body["items"]) == 100
    assert body["truncated"] is True
    assert body["hasMore"] is True
    assert body["nextCursor"] is not None

    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json=[{"name": "only.txt", "path": "only.txt", "type": "file", "size": 1}],
        ),
    )
    complete = await client.get(f"{binding_url(binding_id)}/tree?ref=main&limit=100")
    complete_body = complete.json()
    assert complete_body["truncated"] is False
    assert complete_body["hasMore"] is False
    assert complete_body["nextCursor"] is None


@pytest.mark.asyncio
async def test_tc232_cursor_tamper_and_cross_query_rejected(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    other_id, _ = await create_binding(client, project_id, repo="pay/other")
    await mark_synced(database, binding_id)
    await mark_synced(database, other_id)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/branches"):
            return httpx.Response(
                200,
                json=[{"name": "main", "commit": {"sha": "a" * 40}}],
                headers={
                    "Link": f'<https://api.github.com{path}?page=2>; rel="next"'
                },
            )
        if path.endswith("/commits"):
            return httpx.Response(
                200, json=[commit_item("e", "one", "2026-01-01T00:00:00Z")]
            )
        raise AssertionError(f"未预期的路径：{path}")

    install_transport(monkeypatch, handler)

    page = await client.get(f"{binding_url(binding_id)}/branches?limit=1")
    cursor = page.json()["nextCursor"]
    assert cursor is not None

    valid = await client.get(
        f"{binding_url(binding_id)}/branches?limit=1&cursor={cursor}"
    )
    assert valid.status_code == 200, valid.text

    cross_query = await client.get(
        f"{binding_url(binding_id)}/branches?limit=1&search=pay&cursor={cursor}"
    )
    assert cross_query.status_code == 400
    assert cross_query.json()["code"] == "invalid_cursor"

    cross_endpoint = await client.get(
        f"{binding_url(binding_id)}/commits?ref=main&cursor={cursor}"
    )
    assert cross_endpoint.status_code == 400
    assert cross_endpoint.json()["code"] == "invalid_cursor"

    cross_binding = await client.get(
        f"{binding_url(other_id)}/branches?limit=1&cursor={cursor}"
    )
    assert cross_binding.status_code == 400
    assert cross_binding.json()["code"] == "invalid_cursor"

    tampered = await client.get(
        f"{binding_url(binding_id)}/branches?limit=1&cursor={cursor}x"
    )
    assert tampered.status_code == 400
    assert tampered.json()["code"] == "invalid_cursor"


@pytest.mark.asyncio
async def test_tc233_baseline_reads_snapshot_without_provider(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    await mark_synced(database, binding_id)

    fetched_at = utcnow()
    async with database.sessionmaker() as db:
        db.add_all(
            [
                RepoMetadataSnapshot(
                    snapshot_id=uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    kind="repo",
                    ref="main",
                    payload={
                        "repoId": "pay/checkout",
                        "fullName": "pay/checkout",
                        "defaultBranch": "main",
                        "sha": "a" * 40,
                    },
                    fetched_at=fetched_at,
                ),
                RepoMetadataSnapshot(
                    snapshot_id=uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    kind="branch",
                    ref="main",
                    payload={
                        "name": "main",
                        "isDefault": True,
                        "headSha": "a" * 40,
                        "committedAt": "2026-01-01T00:00:00Z",
                    },
                    fetched_at=fetched_at,
                ),
                RepoMetadataSnapshot(
                    snapshot_id=uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    kind="commit",
                    ref="main",
                    payload={
                        "sha": "a" * 40,
                        "shortSha": "a" * 7,
                        "title": "init",
                        "authorName": "lin.t",
                        "committedAt": "2026-01-01T00:00:00Z",
                    },
                    fetched_at=fetched_at,
                ),
            ]
        )
        await db.commit()

    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(500, json={"message": "boom"})
    )

    response = await client.get(f"{binding_url(binding_id)}/baseline")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metadataSynced"] is True
    assert body["repo"]["repoId"] == "pay/checkout"
    assert body["branches"][0]["name"] == "main"
    assert body["commits"][0]["title"] == "init"
    assert body["lastSyncSuccessAt"] is not None
    assert body["revoked"] is False
    assert body["guide"] is None
    assert calls == []

    unbound = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert unbound.status_code == 200, unbound.text

    after_unbind = await client.get(f"{binding_url(binding_id)}/baseline")
    assert after_unbind.status_code == 200, after_unbind.text
    revoked_body = after_unbind.json()
    assert revoked_body["revoked"] is True
    assert revoked_body["status"] == "revoked"
    assert revoked_body["repo"]["repoId"] == "pay/checkout"
    assert revoked_body["commits"][0]["title"] == "init"
    assert calls == []


@pytest.mark.asyncio
async def test_tc233_baseline_unsynced_guides_sync_first(api, monkeypatch) -> None:
    client, _, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(500, json={"message": "boom"})
    )

    response = await client.get(f"{binding_url(binding_id)}/baseline")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["metadataSynced"] is False
    assert body["repo"] is None
    assert body["branches"] == []
    assert body["commits"] == []
    assert body["lastSyncSuccessAt"] is None
    assert body["guide"] == "sync_first"
    assert calls == []
