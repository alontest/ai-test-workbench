"""GitHub REST 只读适配器（ADR-206 / ADR-209）。

与 design.md 文字的唯一差异：``list_repositories`` 在带 ``search`` 时走
``/search/repositories?q=``，因为 ``/user/repos`` 不接受检索词。
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit

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

_NEXT_LINK = re.compile(r'<([^>]+)>;\s*rel="next"')
_TREE_TRUNCATED_AT = 1000
_EXPIRY_FORMATS = ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S UTC")


def _clamp_limit(limit: int) -> int:
    return max(1, min(100, limit))


def _cursor_page(cursor: str | None) -> int:
    if cursor and cursor.isdigit() and int(cursor) > 0:
        return int(cursor)
    return 1


def _next_page_from_link(headers: httpx.Headers) -> str | None:
    link = header_value(headers, "link") or ""
    match = _NEXT_LINK.search(link)
    if match is None:
        return None
    pages = parse_qs(urlsplit(match.group(1)).query).get("page")
    if not pages or not pages[0].isdigit():
        return None
    return pages[0]


def _repo_segments(ref: RepositoryRef) -> list[str]:
    if "/" in ref.repo_name:
        return ref.repo_name.split("/")
    if ref.owner:
        return [ref.owner, ref.repo_name]
    raise ValueError("GitHub 仓库引用缺少 owner。")


def _repo_path(ref: RepositoryRef) -> str:
    return "/repos/" + "/".join(quote(segment, safe="") for segment in _repo_segments(ref))


def _items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not all(
        isinstance(item, dict) for item in payload
    ):
        raise ProviderError("invalid_response")
    return payload


def _object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProviderError("invalid_response")
    return payload


def _required_str(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value:
        raise ProviderError("invalid_response")
    return value


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
    full_name = _required_str(item, "full_name")
    display_name = item.get("name")
    return RepositorySummary(
        repo_id=full_name,
        full_name=full_name,
        display_name=display_name if isinstance(display_name, str) else full_name,
        default_branch=item.get("default_branch")
        if isinstance(item.get("default_branch"), str)
        else None,
        web_url=item.get("html_url") if isinstance(item.get("html_url"), str) else None,
    )


class GitHubProvider(BaseProvider):
    name: RepoProviderName = "github"

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    def _capture_token_expiry(self, headers: httpx.Headers) -> None:
        raw = header_value(headers, "github-authentication-token-expiration")
        if not raw:
            self.token_expires_at = None
            return
        for fmt in _EXPIRY_FORMATS:
            try:
                self.token_expires_at = datetime.strptime(raw, fmt)
                return
            except ValueError:
                continue
        self.token_expires_at = None

    async def list_repositories(
        self, *, search: str | None, cursor: str | None, limit: int
    ) -> Page[RepositorySummary]:
        page = _cursor_page(cursor)
        per_page = _clamp_limit(limit)
        if search:
            payload, response = await self._get_json(
                "/search/repositories",
                params={"q": search, "per_page": per_page, "page": page},
            )
            body = _object(payload)
            items = _items(body.get("items"))
            total = body.get("total_count")
            total = total if isinstance(total, int) else None
        else:
            payload, response = await self._get_json(
                "/user/repos", params={"per_page": per_page, "page": page}
            )
            items = _items(payload)
            total = None
        return Page(
            items=tuple(_repo_summary(item) for item in items),
            next_cursor=_next_page_from_link(response.headers),
            total=total,
        )

    async def get_repository(self, repo: RepositoryRef) -> RepositorySummary:
        payload, _ = await self._get_json(_repo_path(repo))
        return _repo_summary(_object(payload))

    async def list_branches(
        self,
        repo: RepositoryRef,
        *,
        search: str | None,
        cursor: str | None,
        limit: int,
    ) -> Page[BranchSummary]:
        payload, response = await self._get_json(
            f"{_repo_path(repo)}/branches",
            params={
                "per_page": _clamp_limit(limit),
                "page": _cursor_page(cursor),
            },
        )
        branches: list[BranchSummary] = []
        needle = search.casefold() if search else None
        for item in _items(payload):
            name = _required_str(item, "name")
            if needle is not None and needle not in name.casefold():
                continue
            commit = item.get("commit")
            head_sha = (
                commit.get("sha")
                if isinstance(commit, dict) and isinstance(commit.get("sha"), str)
                else ""
            )
            if not head_sha:
                raise ProviderError("invalid_response")
            branches.append(
                BranchSummary(
                    name=name,
                    is_default=name == repo.default_branch,
                    head_sha=head_sha,
                )
            )
        return Page(
            items=tuple(branches),
            next_cursor=_next_page_from_link(response.headers),
        )

    async def list_commits(
        self,
        repo: RepositoryRef,
        *,
        ref: str,
        cursor: str | None,
        limit: int,
    ) -> Page[CommitSummary]:
        payload, response = await self._get_json(
            f"{_repo_path(repo)}/commits",
            params={
                "sha": ref,
                "per_page": _clamp_limit(limit),
                "page": _cursor_page(cursor),
            },
        )
        commits: list[CommitSummary] = []
        for item in _items(payload):
            sha = _required_str(item, "sha")
            commit = item.get("commit")
            if not isinstance(commit, dict):
                raise ProviderError("invalid_response")
            message = commit.get("message")
            title = message.splitlines()[0] if isinstance(message, str) and message else ""
            author = commit.get("author")
            author_name = (
                author.get("name")
                if isinstance(author, dict) and isinstance(author.get("name"), str)
                else ""
            )
            if not author_name:
                login = item.get("author")
                author_name = (
                    login.get("login")
                    if isinstance(login, dict) and isinstance(login.get("login"), str)
                    else ""
                )
            committed_at = _parse_iso(
                author.get("date") if isinstance(author, dict) else None
            )
            commits.append(
                CommitSummary(
                    sha=sha,
                    short_sha=sha[:7],
                    title=title,
                    author_name=author_name,
                    committed_at=committed_at,
                )
            )
        return Page(
            items=_newest_first(commits),
            next_cursor=_next_page_from_link(response.headers),
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
        encoded = quote(path, safe="/") if path else ""
        payload, _ = await self._get_json(
            f"{_repo_path(repo)}/contents/{encoded}", params={"ref": ref}
        )
        entries: list[TreeEntry] = []
        for item in _items(payload):
            item_type = "dir" if item.get("type") == "dir" else "file"
            size = item.get("size")
            entries.append(
                TreeEntry(
                    name=_required_str(item, "name"),
                    path=_required_str(item, "path"),
                    type=item_type,
                    size_bytes=size
                    if item_type == "file" and isinstance(size, int)
                    else None,
                )
            )
        truncated = len(entries) >= _TREE_TRUNCATED_AT
        return TreePage(
            path=path,
            ref=ref,
            entries=tuple(entries),
            truncated=truncated,
            has_more=False,
            next_cursor=None,
            total=len(entries),
        )

    async def read_file(
        self, repo: RepositoryRef, *, ref: str, path: str
    ) -> FileContent:
        encoded = quote(path, safe="/") if path else ""
        payload, _ = await self._get_json(
            f"{_repo_path(repo)}/contents/{encoded}", params={"ref": ref}
        )
        item = _object(payload)
        size = item.get("size")
        if not isinstance(size, int):
            raise ProviderError("invalid_response")
        if size > REPO_FILE_MAX_BYTES:
            # GitHub 对 >1 MiB 的文件返回 ``encoding=none`` 且不带内容；
            # 供应商侧的 content 字段本身总是 base64。
            raise FileTooLarge(size, REPO_FILE_MAX_BYTES, encoding="base64")
        if item.get("encoding") == "none":
            # 体积未超限却没有内容（子模块 / 稀疏对象等），不是可读文件。
            raise ProviderError("invalid_response")
        content = item.get("content")
        if not isinstance(content, str):
            raise ProviderError("invalid_response")
        return FileContent(
            path=path,
            ref=ref,
            size_bytes=size,
            encoding="base64",
            content=content.replace("\n", "").replace("\r", ""),
        )


__all__ = ["GitHubProvider"]
