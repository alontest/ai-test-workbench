"""仓库集成纯类型与数据载体（无 DB、无网络依赖）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, Protocol, TypeVar

RepoProviderName = Literal["yunxiao", "github"]
BindingStatus = Literal["unverified", "connected", "token_invalid", "revoked"]
TestResult = Literal["success", "auth-error", "unreachable", "permission-denied"]
ProviderErrorCategory = Literal[
    "auth",
    "permission_denied",
    "rate_limited",
    "not_found",
    "network",
    "timeout",
    "server_error",
    "invalid_response",
]
TreeEntryType = Literal["file", "dir"]
FileEncoding = Literal["text", "base64"]

T = TypeVar("T")


class ProviderError(Exception):
    """适配器唯一对外异常；``message`` 只放固定可读文案，不含供应商原文。"""

    def __init__(
        self,
        category: ProviderErrorCategory,
        *,
        status_code: int | None = None,
        retry_after_at: datetime | None = None,
        message: str = "",
    ) -> None:
        self.category = category
        self.status_code = status_code
        self.retry_after_at = retry_after_at
        self.message = message or _DEFAULT_MESSAGES[category]
        super().__init__(self.message)


_DEFAULT_MESSAGES: dict[str, str] = {
    "auth": "供应商令牌无效或已过期。",
    "permission_denied": "供应商拒绝访问或资源不存在。",
    "rate_limited": "供应商限流，请稍后重试。",
    "not_found": "供应商拒绝访问或资源不存在。",
    "network": "无法连接供应商服务。",
    "timeout": "供应商请求超时。",
    "server_error": "供应商服务异常。",
    "invalid_response": "供应商响应无法解析。",
}


@dataclass(frozen=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    next_cursor: str | None = None
    total: int | None = None


@dataclass(frozen=True)
class RepositorySummary:
    repo_id: str
    full_name: str
    display_name: str
    default_branch: str | None = None
    web_url: str | None = None


@dataclass(frozen=True)
class BranchSummary:
    name: str
    is_default: bool
    head_sha: str
    committed_at: datetime | None = None


@dataclass(frozen=True)
class CommitSummary:
    sha: str
    short_sha: str
    title: str
    author_name: str
    committed_at: datetime | None = None


@dataclass(frozen=True)
class TreeEntry:
    name: str
    path: str
    type: TreeEntryType
    size_bytes: int | None = None


@dataclass(frozen=True)
class TreePage:
    path: str
    ref: str
    entries: tuple[TreeEntry, ...]
    truncated: bool = False
    has_more: bool = False
    next_cursor: str | None = None
    total: int | None = None


@dataclass(frozen=True)
class FileContent:
    path: str
    ref: str
    size_bytes: int
    encoding: FileEncoding
    content: str
    fetched_at: datetime | None = None


@dataclass(frozen=True)
class RepositoryRef:
    """适配器调用所需的最小仓库引用；不含令牌。"""

    provider: RepoProviderName
    repo_id: str
    repo_name: str
    api_base_url: str
    org_id: str | None = None
    owner: str | None = None
    default_branch: str | None = None


RepoRef = RepositoryRef


class RepoProvider(Protocol):
    """五类能力、六个方法；供应商差异只存在于适配器内部。"""

    name: RepoProviderName

    async def list_repositories(
        self, *, search: str | None, cursor: str | None, limit: int
    ) -> Page[RepositorySummary]: ...

    async def get_repository(self, repo: RepositoryRef) -> RepositorySummary: ...

    async def list_branches(
        self,
        repo: RepositoryRef,
        *,
        search: str | None,
        cursor: str | None,
        limit: int,
    ) -> Page[BranchSummary]: ...

    async def list_commits(
        self,
        repo: RepositoryRef,
        *,
        ref: str,
        cursor: str | None,
        limit: int,
    ) -> Page[CommitSummary]: ...

    async def list_tree(
        self,
        repo: RepositoryRef,
        *,
        ref: str,
        path: str,
        cursor: str | None,
        limit: int,
    ) -> TreePage: ...

    async def read_file(
        self, repo: RepositoryRef, *, ref: str, path: str
    ) -> FileContent: ...


__all__ = [
    "BindingStatus",
    "BranchSummary",
    "CommitSummary",
    "FileContent",
    "FileEncoding",
    "Page",
    "ProviderError",
    "ProviderErrorCategory",
    "RepoProvider",
    "RepoProviderName",
    "RepoRef",
    "RepositoryRef",
    "RepositorySummary",
    "TestResult",
    "TreeEntry",
    "TreeEntryType",
    "TreePage",
]
