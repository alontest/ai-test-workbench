"""阿里云云效 Codeup 只读适配器（ADR-206 / ADR-209）。

中心站前缀 ``/oapi/v1/codeup/organizations/{orgId}/repositories``；
地域站（自定义域名）省略 ``organizations`` 段。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from workbench.repos.constants import REPO_FILE_MAX_BYTES
from workbench.repos.providers.base import BaseProvider, FileTooLarge, header_value
from workbench.repos.types import (
    BranchSummary,
    CommitSummary,
    FileContent,
    Page,
    ProviderError,
    RepoProviderName,
    RepositoryRef,
    RepositorySummary,
    TreeEntry,
    TreePage,
)
from workbench.repos.validation import YUNXIAO_API_BASE_URL

_API_PREFIX = "/oapi/v1/codeup"
_VALID_ENCODINGS = ("text", "base64")


def _clamp_limit(limit: int) -> int:
    return max(1, min(100, limit))


def _cursor_page(cursor: str | None) -> int:
    if cursor and cursor.isdigit() and int(cursor) > 0:
        return int(cursor)
    return 1


def _page_cursor(headers: httpx.Headers, page: int) -> str | None:
    """终止条件用 ``x-next-page`` / ``x-total-pages``，不用 ``x-total`` 推算页数。

    ``x-next-page`` 存在即以其为准：指向当前页或更小（含 0）表示已到末页。
    """
    next_page = (header_value(headers, "x-next-page") or "").strip()
    if next_page:
        if next_page.isdigit() and int(next_page) > page:
            return str(int(next_page))
        return None
    total_pages = (header_value(headers, "x-total-pages") or "").strip()
    if total_pages.isdigit() and int(total_pages) > page:
        return str(page + 1)
    return None


def _total(headers: httpx.Headers) -> int | None:
    raw = (header_value(headers, "x-total") or "").strip()
    return int(raw) if raw.isdigit() else None


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict) and "result" in payload:
        return payload["result"]
    return payload


def _list(payload: Any) -> list[dict[str, Any]]:
    result = _unwrap(payload)
    if not isinstance(result, list) or not all(
        isinstance(item, dict) for item in result
    ):
        raise ProviderError("invalid_response")
    return result


def _as_int(value: Any) -> int | None:
    """云效同一字段可能给 int 或数字字符串；非法值返回 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _object(payload: Any) -> dict[str, Any]:
    result = _unwrap(payload)
    if not isinstance(result, dict):
        raise ProviderError("invalid_response")
    return result


# 云效 ``ListFiles`` 用 git 对象类型命名：``tree`` 是目录，``blob`` 是文件。
# 2026-11-21 用真实组织验证时发现：原实现只认 ``"dir"``，把全部目录都判成了
# 文件，导致点开目录去读文件、返回 404。这里按真实值判断，并用 git mode
# （``040000`` 为目录）兜底，避免供应商改字段名时再退化。
_TREE_TYPES = frozenset({"tree", "dir", "directory", "folder"})
_BLOB_TYPES = frozenset({"blob", "file"})
_GIT_MODE_DIR = "040000"


def _entry_type(item: dict[str, Any]) -> str:
    raw = item.get("type")
    if isinstance(raw, str):
        lowered = raw.strip().lower()
        if lowered in _TREE_TYPES:
            return "dir"
        if lowered in _BLOB_TYPES:
            return "file"
    if str(item.get("mode") or "").strip() == _GIT_MODE_DIR:
        return "dir"
    return "file"


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    if isinstance(value, int):
        return str(value)
    return None


def _required(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = _text(item.get(key))
        if value is not None:
            return value
    raise ProviderError("invalid_response")


def _first_text(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _text(item.get(key))
        if value is not None:
            return value
    return None


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _newest_first(commits: list[CommitSummary]) -> tuple[CommitSummary, ...]:
    """同页内按提交时间倒序；时间未知的排到最后，不丢条目。"""
    return tuple(
        sorted(
            commits,
            key=lambda item: item.committed_at or datetime.min,
            reverse=True,
        )
    )


def _repo_summary(item: dict[str, Any]) -> RepositorySummary:
    repo_id = _required(item, "id", "pathWithNamespace", "path")
    full_name = _first_text(item, "pathWithNamespace", "path", "name") or repo_id
    display_name = _first_text(item, "name", "path") or full_name
    return RepositorySummary(
        repo_id=repo_id,
        full_name=full_name,
        display_name=display_name,
        default_branch=_first_text(item, "defaultBranch", "defaultBranchName"),
        web_url=_first_text(item, "webUrl", "httpUrlToRepo"),
    )


def _is_default_branch(item: dict[str, Any]) -> bool:
    for key in ("isDefault", "isDefaultBranch"):
        value = item.get(key)
        if isinstance(value, bool):
            return value
    value = item.get("defaultBranch")
    return value is True


class YunxiaoProvider(BaseProvider):
    name: RepoProviderName = "yunxiao"

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"x-yunxiao-token": token}

    def _repo_base(self) -> str:
        if self._ref.api_base_url.rstrip("/") != YUNXIAO_API_BASE_URL:
            return f"{_API_PREFIX}/repositories"
        org_id = self._ref.org_id
        if not org_id:
            raise ValueError("云效中心站需要 org_id。")
        return f"{_API_PREFIX}/organizations/{quote(org_id, safe='')}/repositories"

    def _repo_path(self, repo: RepositoryRef) -> str:
        repo_id = repo.repo_id or repo.repo_name
        if not repo_id:
            raise ValueError("云效仓库引用缺少 repo_id。")
        return f"{self._repo_base()}/{quote(repo_id, safe='')}"

    async def list_repositories(
        self, *, search: str | None, cursor: str | None, limit: int
    ) -> Page[RepositorySummary]:
        payload, response = await self._get_json(
            self._repo_base(),
            params={
                "page": _cursor_page(cursor),
                "perPage": _clamp_limit(limit),
                "search": search,
            },
        )
        return Page(
            items=tuple(_repo_summary(item) for item in _list(payload)),
            next_cursor=_page_cursor(
                response.headers, _cursor_page(cursor)
            ),
            total=_total(response.headers),
        )

    async def get_repository(self, repo: RepositoryRef) -> RepositorySummary:
        payload, _ = await self._get_json(self._repo_path(repo))
        return _repo_summary(_object(payload))

    async def list_branches(
        self,
        repo: RepositoryRef,
        *,
        search: str | None,
        cursor: str | None,
        limit: int,
    ) -> Page[BranchSummary]:
        page = _cursor_page(cursor)
        payload, response = await self._get_json(
            f"{self._repo_path(repo)}/branches",
            params={"page": page, "perPage": _clamp_limit(limit), "search": search},
        )
        branches: list[BranchSummary] = []
        for item in _list(payload):
            name = _required(item, "name", "branchName")
            head_sha = _first_text(item, "headSha", "sha")
            if head_sha is None:
                commit = item.get("commit")
                if isinstance(commit, dict):
                    head_sha = _first_text(commit, "id")
            if head_sha is None:
                raise ProviderError("invalid_response")
            branches.append(
                BranchSummary(
                    name=name,
                    is_default=_is_default_branch(item),
                    head_sha=head_sha,
                )
            )
        return Page(
            items=tuple(branches),
            next_cursor=_page_cursor(response.headers, page),
            total=_total(response.headers),
        )

    async def list_commits(
        self,
        repo: RepositoryRef,
        *,
        ref: str,
        cursor: str | None,
        limit: int,
    ) -> Page[CommitSummary]:
        page = _cursor_page(cursor)
        payload, response = await self._get_json(
            f"{self._repo_path(repo)}/commits",
            params={
                "refName": ref,
                "page": page,
                "perPage": _clamp_limit(limit),
            },
        )
        commits: list[CommitSummary] = []
        for item in _list(payload):
            sha = _required(item, "id")
            title = _first_text(item, "title")
            if title is None:
                message = item.get("message")
                title = message.splitlines()[0] if isinstance(message, str) else ""
            author_name = _first_text(item, "authorName")
            if author_name is None:
                author = item.get("author")
                if isinstance(author, dict):
                    author_name = _first_text(author, "name")
            commits.append(
                CommitSummary(
                    sha=sha,
                    short_sha=_first_text(item, "shortId") or sha[:7],
                    title=title or "",
                    author_name=author_name or "",
                    committed_at=_parse_iso(
                        _first_text(item, "authoredDate", "committedDate")
                    ),
                )
            )
        return Page(
            items=_newest_first(commits),
            next_cursor=_page_cursor(response.headers, page),
            total=_total(response.headers),
        )

    async def list_tree(
        self,
        repo: RepositoryRef,
        *,
        ref: str,
        path: str,
        cursor: str | None,
        limit: int,
    ) -> TreePage:
        payload, _ = await self._get_json(
            f"{self._repo_path(repo)}/files/tree",
            params={"path": path, "ref": ref, "type": "DIRECT"},
        )
        entries: list[TreeEntry] = []
        for item in _list(payload):
            entries.append(
                TreeEntry(
                    name=_required(item, "name"),
                    path=_required(item, "path"),
                    type=_entry_type(item),
                    size_bytes=None,
                )
            )
        return TreePage(
            path=path,
            ref=ref,
            entries=tuple(entries),
            truncated=False,
            has_more=False,
            next_cursor=None,
            total=len(entries),
        )

    async def read_file(
        self, repo: RepositoryRef, *, ref: str, path: str
    ) -> FileContent:
        # 官方语法：GET .../repositories/{repoId}/files/{rest:.*}?ref=<ref>
        # 文件路径是**路径段**（需 URL 编码），不是 /files/blobs 加 filePath 查询参数。
        # 2026-11-21 用真实组织验证：用 /files/blobs 时云效把 "blobs" 当成文件路径，
        # 报 404 "revision(main) path(blobs) not found"。
        # 官方文档写「文件路径需 URL 编码」，实测含义是连 `/` 也要编码：
        # 保留 `/` 会 404，`%2F` 才 200（2026-11-21 实测 jialeshop-core/pom.xml）。
        encoded = quote(path, safe="")
        payload, _ = await self._get_json(
            f"{self._repo_path(repo)}/files/{encoded}",
            params={"ref": ref},
        )
        item = _object(payload)
        # 云效的 size 有时是 int、有时是字符串（同一端点在不同请求头下不一致，
        # 2026-11-21 实测：裸 curl 返回 int 14948，带 Accept 头返回 "14948"）。
        # 两种都要接受，否则真实调用会报 invalid_response。
        size = _as_int(item.get("size"))
        if size is None:
            raise ProviderError("invalid_response")
        encoding = item.get("encoding", "base64")
        if encoding not in _VALID_ENCODINGS:
            raise ProviderError("invalid_response")
        if size > REPO_FILE_MAX_BYTES:
            raise FileTooLarge(size, REPO_FILE_MAX_BYTES, encoding=encoding)
        content = item.get("content")
        if not isinstance(content, str):
            raise ProviderError("invalid_response")
        return FileContent(
            path=path,
            ref=ref,
            size_bytes=size,
            encoding=encoding,
            content=content,
        )


__all__ = ["YunxiaoProvider"]
