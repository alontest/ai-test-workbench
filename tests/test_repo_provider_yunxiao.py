"""云效 Codeup 适配器：中心站/地域站路径、六方法归一化与错误映射。"""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from workbench.repos.providers.yunxiao import YunxiaoProvider
from workbench.repos.types import ProviderError, RepositoryRef

TOKEN = "yx_test_token_value"
CENTER = "https://openapi-rdc.aliyuncs.com"
REGIONAL = "https://code.example.com"
CENTER_BASE = "/oapi/v1/codeup/organizations/12345/repositories"


def _ref(**overrides: object) -> RepositoryRef:
    values: dict[str, object] = {
        "provider": "yunxiao",
        "repo_id": "67890",
        "repo_name": "group/repo",
        "api_base_url": CENTER,
        "org_id": "12345",
        "default_branch": "master",
    }
    values.update(overrides)
    return RepositoryRef(**values)  # type: ignore[arg-type]


def _provider(handler, ref: RepositoryRef | None = None) -> YunxiaoProvider:  # noqa: ANN001
    return YunxiaoProvider(ref or _ref(), TOKEN, transport=httpx.MockTransport(handler))


REPO_ITEM = {
    "id": 67890,
    "pathWithNamespace": "group/repo",
    "name": "repo",
    "defaultBranch": "master",
    "webUrl": "https://codeup.example.com/group/repo",
}


async def test_tc208_yunxiao_six_methods_normalize_success() -> None:
    # Arrange
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == CENTER_BASE:
            return httpx.Response(
                200,
                json={"result": [REPO_ITEM]},
                headers={"x-next-page": "2", "x-total": "3", "x-total-pages": "2"},
            )
        if path == f"{CENTER_BASE}/67890":
            return httpx.Response(200, json=REPO_ITEM)
        if path == f"{CENTER_BASE}/67890/branches":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": "master", "isDefault": True, "commit": {"id": "s1"}},
                        {"branchName": "dev", "sha": "s2"},
                    ]
                },
                headers={"x-total-pages": "1"},
            )
        if path == f"{CENTER_BASE}/67890/commits":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "id": "abc1234def",
                            "shortId": "abc1234",
                            "title": "feat: x",
                            "authorName": "Alon",
                            "authoredDate": "2026-01-02T03:04:05+08:00",
                        },
                        {
                            "id": "deadbeefcafe",
                            "message": "fix y\n\nbody",
                            "author": {"name": "Bo"},
                            "committedDate": "2026-02-03T04:05:06Z",
                        },
                    ]
                },
                headers={"x-total-pages": "5"},
            )
        if path == f"{CENTER_BASE}/67890/files/tree":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": "src", "path": "src", "type": "DIRECTORY"},
                        {"name": "README.md", "path": "README.md", "type": "FILE"},
                    ]
                },
            )
        if path == f"{CENTER_BASE}/67890/files/blobs":
            return httpx.Response(
                200,
                json={
                    "result": {"size": 12, "encoding": "text", "content": "hello world"}
                },
            )
        raise AssertionError(f"未预期的路径：{path}")

    provider = _provider(handler)
    repo = _ref()

    # Act
    repos = await provider.list_repositories(search=None, cursor=None, limit=2)
    detail = await provider.get_repository(repo)
    branches = await provider.list_branches(repo, search=None, cursor=None, limit=30)
    commits = await provider.list_commits(repo, ref="master", cursor=None, limit=30)
    tree = await provider.list_tree(repo, ref="master", path="", cursor=None, limit=100)
    file = await provider.read_file(repo, ref="master", path="README.md")
    await provider.aclose()

    # Assert
    assert repos.items[0].repo_id == "67890"
    assert repos.items[0].full_name == "group/repo"
    assert repos.items[0].display_name == "repo"
    assert repos.items[0].default_branch == "master"
    assert repos.items[0].web_url == "https://codeup.example.com/group/repo"
    assert repos.next_cursor == "2"
    assert repos.total == 3

    assert detail.full_name == "group/repo"

    assert [branch.name for branch in branches.items] == ["master", "dev"]
    assert branches.items[0].is_default is True
    assert branches.items[0].head_sha == "s1"
    assert branches.items[1].is_default is False
    assert branches.items[1].head_sha == "s2"

    assert commits.items[0].sha == "deadbeefcafe"
    assert commits.items[0].short_sha == "deadbee"
    assert commits.items[0].title == "fix y"
    assert commits.items[0].author_name == "Bo"
    assert commits.items[0].committed_at == datetime(2026, 2, 3, 4, 5, 6)
    assert commits.items[1].sha == "abc1234def"
    assert commits.items[1].short_sha == "abc1234"
    assert commits.items[1].title == "feat: x"
    assert commits.items[1].author_name == "Alon"
    assert commits.items[1].committed_at == datetime(2026, 1, 1, 19, 4, 5)
    assert commits.next_cursor == "2"

    assert [entry.type for entry in tree.entries] == ["dir", "file"]

    assert file.size_bytes == 12
    assert file.encoding == "text"
    assert file.content == "hello world"

    assert all(request.method == "GET" for request in requests)
    assert all(
        request.headers["x-yunxiao-token"] == TOKEN for request in requests
    )
    assert all(TOKEN not in str(request.url) for request in requests)
    commits_request = next(
        request for request in requests if request.url.path.endswith("/commits")
    )
    assert commits_request.url.params["refName"] == "master"


async def test_tc208_yunxiao_regional_base_omits_organizations() -> None:
    # Arrange
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=REPO_ITEM)

    provider = _provider(handler, _ref(api_base_url=REGIONAL, org_id=None))

    # Act
    detail = await provider.get_repository(_ref(api_base_url=REGIONAL, org_id=None))
    await provider.aclose()

    # Assert
    assert detail.repo_id == "67890"
    assert requests[0].url.path == "/oapi/v1/codeup/repositories/67890"
    assert "organizations" not in requests[0].url.path


async def test_tc208_yunxiao_tree_direct_has_no_pagination() -> None:
    # Arrange
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"result": [{"name": "src", "path": "src", "type": "DIRECTORY"}]}
        )

    provider = _provider(handler)

    # Act
    tree = await provider.list_tree(
        _ref(), ref="master", path="", cursor=None, limit=100
    )
    await provider.aclose()

    # Assert
    assert requests[0].url.params["type"] == "DIRECT"
    assert requests[0].url.params["ref"] == "master"
    assert tree.has_more is False
    assert tree.next_cursor is None
    assert tree.truncated is False
    assert tree.entries[0].type == "dir"


async def test_tc208_yunxiao_file_blob_encodes_file_path() -> None:
    # Arrange
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200, json={"result": {"size": 3, "encoding": "base64", "content": "YWJj"}}
        )

    provider = _provider(handler)

    # Act
    file = await provider.read_file(_ref(), ref="main", path="src/main.py")
    await provider.aclose()

    # Assert
    assert requests[0].url.path.endswith("/67890/files/blobs")
    assert requests[0].url.params["filePath"] == "src/main.py"
    assert requests[0].url.params["ref"] == "main"
    assert TOKEN not in str(requests[0].url)
    assert file.encoding == "base64"
    assert file.content == "YWJj"


async def test_tc209_yunxiao_401_classified_auth() -> None:
    # Arrange
    provider = _provider(
        lambda request: httpx.Response(401, json={"errorMessage": "token invalid"})
    )

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "auth"
    assert info.value.status_code == 401
    assert TOKEN not in str(info.value)
    assert "token invalid" not in info.value.message


async def test_tc210_yunxiao_timeout_and_network() -> None:
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


async def test_tc211_yunxiao_403_without_signal_is_permission_denied() -> None:
    # Arrange
    provider = _provider(
        lambda request: httpx.Response(403, json={"errorMessage": "forbidden"})
    )

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "permission_denied"
    assert info.value.status_code == 403


async def test_tc213_yunxiao_429_rate_limited_without_retry_header() -> None:
    # Arrange
    provider = _provider(
        lambda request: httpx.Response(429, json={"errorMessage": "Too many requests"})
    )

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "rate_limited"
    assert info.value.status_code == 429
    assert info.value.retry_after_at is None


async def test_tc234_yunxiao_invalid_json_is_invalid_response() -> None:
    # Arrange
    provider = _provider(
        lambda request: httpx.Response(200, content=b"<html>not json</html>")
    )

    # Act / Assert
    with pytest.raises(ProviderError) as info:
        await provider.get_repository(_ref())
    await provider.aclose()

    assert info.value.category == "invalid_response"
    assert "<html>" not in str(info.value)


async def test_tc214_yunxiao_never_invents_token_expiry() -> None:
    # Arrange
    provider = _provider(lambda request: httpx.Response(200, json=REPO_ITEM))

    # Act
    await provider.get_repository(_ref())
    await provider.aclose()

    # Assert
    assert provider.token_expires_at is None


async def test_tc225_yunxiao_branches_page_by_next_page_header() -> None:
    # Arrange
    pages: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        page = request.url.params.get("page")
        pages.append(page)
        if page == "1":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"name": "master", "isDefault": True, "commit": {"id": "s1"}},
                        {"name": "dev", "commit": {"id": "s2"}},
                    ]
                },
                headers={
                    "x-next-page": "2",
                    "x-total": "999",
                    "x-total-pages": "2",
                },
            )
        return httpx.Response(
            200,
            json={"result": [{"name": "release", "commit": {"id": "s3"}}]},
            headers={"x-next-page": "0", "x-total": "999", "x-total-pages": "2"},
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
    assert [branch.name for branch in first.items] == ["master", "dev"]
    assert [branch.name for branch in second.items] == ["release"]
    assert second.next_cursor is None
    assert first.items[0].is_default is True


async def test_tc225_yunxiao_total_pages_used_only_without_next_page() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("page") == "1":
            return httpx.Response(
                200,
                json={"result": [{"name": "master", "commit": {"id": "s1"}}]},
                headers={"x-total": "999", "x-total-pages": "2"},
            )
        return httpx.Response(
            200,
            json={"result": [{"name": "dev", "commit": {"id": "s2"}}]},
            headers={"x-total": "999", "x-total-pages": "2"},
        )

    provider = _provider(handler)

    # Act
    first = await provider.list_branches(
        _ref(), search=None, cursor=None, limit=100
    )
    second = await provider.list_branches(
        _ref(), search=None, cursor=first.next_cursor, limit=100
    )
    await provider.aclose()

    # Assert
    assert first.next_cursor == "2"
    assert second.next_cursor is None


async def test_tc229_yunxiao_commits_desc_short_sha_and_empty() -> None:
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("refName") == "empty":
            return httpx.Response(200, json={"result": []})
        return httpx.Response(
            200,
            json={
                "result": [
                    {
                        "id": "aaa1111bbb",
                        "title": "older",
                        "authorName": "Bo",
                        "authoredDate": "2026-01-01T00:00:00Z",
                    },
                    {
                        "id": "ccc3333ddd",
                        "title": "newest",
                        "authorName": "Cy",
                        "authoredDate": "2026-03-01T00:00:00Z",
                    },
                    {
                        "id": "bbb2222ccc",
                        "title": "middle",
                        "authorName": "Al",
                        "authoredDate": "2026-02-01T00:00:00Z",
                    },
                ]
            },
        )

    provider = _provider(handler)
    repo = _ref()

    # Act
    page = await provider.list_commits(repo, ref="master", cursor=None, limit=100)
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
