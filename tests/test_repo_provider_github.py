"""GitHub 适配器：六方法归一化、错误映射、过期头与响应体上限。"""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from vigil_workbench.repos.constants import REPO_METADATA_MAX_BYTES
from vigil_workbench.repos.providers.github import GitHubProvider
from vigil_workbench.repos.types import ProviderError, RepositoryRef

TOKEN = "ghp_test_token_value"


def _ref(**overrides: object) -> RepositoryRef:
    values: dict[str, object] = {
        "provider": "github",
        "repo_id": "pay/checkout",
        "repo_name": "pay/checkout",
        "api_base_url": "https://api.github.com",
        "owner": "pay",
        "default_branch": "main",
    }
    values.update(overrides)
    return RepositoryRef(**values)  # type: ignore[arg-type]


def _provider(handler) -> GitHubProvider:  # noqa: ANN001
    return GitHubProvider(_ref(), TOKEN, transport=httpx.MockTransport(handler))


def _repo_item(full_name: str = "pay/checkout", name: str = "checkout") -> dict:
    return {
        "full_name": full_name,
        "name": name,
        "default_branch": "main",
        "html_url": f"https://github.com/{full_name}",
    }


async def test_tc208_github_six_methods_normalize_success() -> None:
    # Arrange
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        page = request.url.params.get("page")
        if path == "/user/repos":
            if page == "1":
                return httpx.Response(
                    200,
                    json=[_repo_item()],
                    headers={
                        "Link": '<https://api.github.com/user/repos?per_page=2&page=2>; rel="next"'
                    },
                )
            return httpx.Response(200, json=[_repo_item("pay/ledger", "ledger")])
        if path == "/repos/pay/checkout":
            return httpx.Response(200, json=_repo_item())
        if path == "/repos/pay/checkout/branches":
            return httpx.Response(
                200,
                json=[
                    {"name": "main", "commit": {"sha": "a" * 40}},
                    {"name": "dev", "commit": {"sha": "b" * 40}},
                ],
            )
        if path == "/repos/pay/checkout/commits":
            return httpx.Response(
                200,
                json=[
                    {
                        "sha": "c" * 40,
                        "commit": {
                            "message": "init commit\n\nbody",
                            "author": {"name": "Alon", "date": "2026-01-02T03:04:05Z"},
                        },
                    }
                ],
            )
        if path == "/repos/pay/checkout/contents/src":
            return httpx.Response(
                200,
                json=[
                    {"name": "main.py", "path": "src/main.py", "type": "file", "size": 12},
                    {"name": "pkg", "path": "src/pkg", "type": "dir", "size": 0},
                ],
            )
        if path == "/repos/pay/checkout/contents/README.md":
            return httpx.Response(
                200,
                json={
                    "name": "README.md",
                    "path": "README.md",
                    "size": 8,
                    "encoding": "base64",
                    "content": "aGVsbG8=\n",
                },
            )
        raise AssertionError(f"未预期的路径：{path}")

    provider = _provider(handler)
    repo = _ref()

    # Act
    first = await provider.list_repositories(search=None, cursor=None, limit=2)
    second = await provider.list_repositories(search=None, cursor="2", limit=2)
    detail = await provider.get_repository(repo)
    branches = await provider.list_branches(repo, search=None, cursor=None, limit=30)
    commits = await provider.list_commits(repo, ref="main", cursor=None, limit=30)
    tree = await provider.list_tree(repo, ref="main", path="src", cursor=None, limit=100)
    file = await provider.read_file(repo, ref="main", path="README.md")
    await provider.aclose()

    # Assert
    assert first.items[0].repo_id == "pay/checkout"
    assert first.items[0].display_name == "checkout"
    assert first.next_cursor == "2"
    assert second.items[0].full_name == "pay/ledger"
    assert second.next_cursor is None

    assert detail.full_name == "pay/checkout"
    assert detail.default_branch == "main"
    assert detail.web_url == "https://github.com/pay/checkout"

    assert [branch.name for branch in branches.items] == ["main", "dev"]
    assert branches.items[0].is_default is True
    assert branches.items[1].is_default is False
    assert branches.items[1].head_sha == "b" * 40

    assert commits.items[0].short_sha == ("c" * 40)[:7]
    assert commits.items[0].title == "init commit"
    assert commits.items[0].author_name == "Alon"
    assert commits.items[0].committed_at == datetime(2026, 1, 2, 3, 4, 5)

    assert [entry.type for entry in tree.entries] == ["file", "dir"]
    assert tree.entries[0].size_bytes == 12
    assert tree.entries[1].size_bytes is None

    assert file.encoding == "base64"
    assert file.content == "aGVsbG8="
    assert file.size_bytes == 8

    assert all(request.method == "GET" for request in requests)
    assert all(request.headers["authorization"] == f"Bearer {TOKEN}" for request in requests)
    assert all(TOKEN not in str(request.url) for request in requests)


async def test_tc208_github_tree_marks_truncated_at_1000() -> None:
    # Arrange
    entries = [
        {"name": f"f{i}.txt", "path": f"f{i}.txt", "type": "file", "size": 1}
        for i in range(1000)
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=entries)

    provider = _provider(handler)

    # Act
    tree = await provider.list_tree(_ref(), ref="main", path="", cursor=None, limit=100)
    await provider.aclose()

    # Assert
    assert len(tree.entries) == 1000
    assert tree.truncated is True
    assert tree.has_more is False
    assert tree.next_cursor is None


async def test_tc209_github_401_classified_auth() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    provider = _provider(handler)

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "auth"
    assert info.value.status_code == 401
    assert TOKEN not in str(info.value)
    assert "Bad credentials" not in info.value.message


async def test_tc210_github_network_and_timeout() -> None:
    # Arrange
    def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns failed")

    def read_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("too slow")

    network_provider = _provider(connect_error)
    timeout_provider = _provider(read_timeout)

    # Act / Assert
    with pytest.raises(ProviderError) as network:
        await network_provider.get_repository(_ref())
    with pytest.raises(ProviderError) as timeout:
        await timeout_provider.get_repository(_ref())
    await network_provider.aclose()
    await timeout_provider.aclose()

    assert network.value.category == "network"
    assert timeout.value.category == "timeout"


async def test_tc211_github_403_without_signal_is_permission_denied() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "Forbidden"})

    provider = _provider(handler)

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "permission_denied"
    assert info.value.status_code == 403


@pytest.mark.parametrize(
    ("status_code", "headers", "body", "expected", "expect_retry"),
    [
        (401, {}, b"{}", "auth", False),
        (403, {"Retry-After": "30"}, b"{}", "rate_limited", True),
        (403, {"X-RateLimit-Remaining": "0"}, b"{}", "rate_limited", False),
        (403, {}, b'{"message": "API rate limit exceeded"}', "rate_limited", False),
        (403, {}, b'{"message": "Forbidden"}', "permission_denied", False),
        (404, {}, b"{}", "not_found", False),
        (429, {}, b"{}", "rate_limited", False),
        (500, {}, b"{}", "server_error", False),
        (418, {}, b"{}", "invalid_response", False),
        (200, {"X-RateLimit-Remaining": "0"}, b"{}", "rate_limited", False),
        (200, {}, b"not-json", "invalid_response", False),
    ],
)
async def test_tc213_provider_error_mapping_table(
    status_code: int,
    headers: dict[str, str],
    body: bytes,
    expected: str,
    expect_retry: bool,
) -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, headers=headers, content=body)

    provider = _provider(handler)

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == expected
    assert info.value.status_code == status_code
    if expect_retry:
        assert info.value.retry_after_at is not None
    else:
        assert info.value.retry_after_at is None


async def test_tc214_github_token_expiration_header() -> None:
    # Arrange
    def make_handler(header: str | None):
        def handler(request: httpx.Request) -> httpx.Response:
            headers = (
                {"GitHub-Authentication-Token-Expiration": header} if header else {}
            )
            return httpx.Response(200, json=_repo_item(), headers=headers)

        return handler

    parsed_utc = _provider(make_handler("2026-12-31 23:59:59 UTC"))
    parsed_iso = _provider(make_handler("2027-01-02T03:04:05Z"))
    absent = _provider(make_handler(None))
    malformed = _provider(make_handler("soon"))

    # Act
    await parsed_utc.get_repository(_ref())
    await parsed_iso.get_repository(_ref())
    await absent.get_repository(_ref())
    await malformed.get_repository(_ref())
    await parsed_utc.aclose()
    await parsed_iso.aclose()
    await absent.aclose()
    await malformed.aclose()

    # Assert
    assert parsed_utc.token_expires_at == datetime(2026, 12, 31, 23, 59, 59)
    assert parsed_iso.token_expires_at == datetime(2027, 1, 2, 3, 4, 5)
    assert absent.token_expires_at is None
    assert malformed.token_expires_at is None


async def test_tc234_metadata_response_cap_and_invalid_json() -> None:
    # Arrange
    oversized = _provider(
        lambda request: httpx.Response(
            200, content=b"x" * (REPO_METADATA_MAX_BYTES + 1)
        )
    )
    malformed = _provider(
        lambda request: httpx.Response(200, content=b"<html>not json</html>")
    )

    # Act / Assert
    with pytest.raises(ProviderError) as too_large:
        await oversized.get_repository(_ref())
    with pytest.raises(ProviderError) as bad_json:
        await malformed.get_repository(_ref())
    await oversized.aclose()
    await malformed.aclose()

    assert too_large.value.category == "invalid_response"
    assert bad_json.value.category == "invalid_response"
    assert "xxxx" not in str(too_large.value)
    assert "<html>" not in str(bad_json.value)


async def test_tc225_github_branches_page_until_link_absent() -> None:
    # Arrange
    pages: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        pages.append(page)
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

    provider = _provider(handler)
    repo = _ref()

    # Act
    first = await provider.list_branches(repo, search=None, cursor=None, limit=2)
    second = await provider.list_branches(
        repo, search=None, cursor=first.next_cursor, limit=2
    )
    await provider.aclose()

    # Assert
    assert pages == ["1", "2"]
    assert first.next_cursor == "2"
    assert [branch.name for branch in first.items] == ["main", "dev"]
    assert [branch.name for branch in second.items] == ["release"]
    assert second.next_cursor is None
    assert first.items[0].is_default is True
    assert first.items[0].head_sha == "a" * 40
    assert second.items[0].is_default is False


async def test_tc225_github_empty_branches_stop_immediately() -> None:
    # Arrange
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=[])

    provider = _provider(handler)

    # Act
    page = await provider.list_branches(
        _ref(), search=None, cursor=None, limit=100
    )
    await provider.aclose()

    # Assert
    assert page.items == ()
    assert page.next_cursor is None
    assert len(calls) == 1


async def test_tc229_github_commits_desc_short_sha_and_empty() -> None:
    # Arrange
    commits = [
        {
            "sha": "b" * 40,
            "commit": {
                "message": "older",
                "author": {"name": "Bo", "date": "2026-01-01T00:00:00Z"},
            },
        },
        {
            "sha": "c" * 40,
            "commit": {
                "message": "newest",
                "author": {"name": "Cy", "date": "2026-03-01T00:00:00Z"},
            },
        },
        {
            "sha": "a" * 40,
            "commit": {
                "message": "middle",
                "author": {"name": "Al", "date": "2026-02-01T00:00:00Z"},
            },
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("sha") == "empty":
            return httpx.Response(200, json=[])
        return httpx.Response(200, json=commits)

    provider = _provider(handler)
    repo = _ref()

    # Act
    page = await provider.list_commits(repo, ref="main", cursor=None, limit=100)
    empty = await provider.list_commits(
        repo, ref="empty", cursor=None, limit=100
    )
    await provider.aclose()

    # Assert
    assert [item.title for item in page.items] == ["newest", "middle", "older"]
    assert [item.committed_at for item in page.items] == sorted(
        [item.committed_at for item in page.items], reverse=True
    )
    assert all(len(item.short_sha) == 7 for item in page.items)
    assert empty.items == ()
