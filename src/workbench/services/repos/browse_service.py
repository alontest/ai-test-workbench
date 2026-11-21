"""实时浏览与跨域只读基线（ADR-208 / ADR-209）。

仓库 / 分支 / 提交 / 目录树全部实时请求供应商；从未成功同步时返回
200 空态且不发外呼。目录树按层级懒加载，``truncated``（供应商不完整）
与 ``hasMore``（还有下一页）互相独立。
"""

from __future__ import annotations

from workbench.db.engine import get_sessionmaker
from workbench.db.repositories.repos import RepoRepository
from workbench.repos.cursor import (
    decode_page_cursor,
    encode_page_cursor,
    fingerprint_query,
)
from workbench.repos.types import RepositoryRef, TreeEntry
from workbench.repos.validation import (
    normalize_repo_key,
    validate_ref,
    validate_repo_path,
    validate_search,
)
from workbench.services.repos.binding_service import (
    repo_cursor_key,
    require_binding,
)
from workbench.services.repos.live_access import (
    LiveBinding,
    load_live_binding,
    open_provider,
    run_provider_call,
    select_repository,
)
from workbench.services.repos.serializers import (
    serialize_baseline_document,
    serialize_branch,
    serialize_commit,
    serialize_repository,
    serialize_tree_entry,
)

EMPTY_GUIDE = "sync_first"


def _empty_payload(
    *, path: str | None = None, ref: str | None = None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "metadataSynced": False,
        "live": False,
        "items": [],
        "nextCursor": None,
        "total": None,
        "guide": EMPTY_GUIDE,
    }
    if path is not None:
        payload.update(
            {
                "path": path,
                "ref": ref,
                "truncated": False,
                "hasMore": False,
            }
        )
    return payload


def _cursor_context(
    live: LiveBinding,
    selected: RepositoryRef,
    *,
    ref: str | None = None,
    path: str | None = None,
    search: str | None = None,
) -> dict[str, object]:
    """游标绑定绑定行、选中仓库、ref、path 与检索词指纹。"""
    return {
        "binding_id": live.binding_id,
        "provider": live.provider,
        "repo_key": normalize_repo_key(live.provider, selected.repo_name),
        "ref": ref,
        "path": path,
        "query_fingerprint": fingerprint_query(search),
    }


def _decode_page(cursor: str | None, key: bytes, context: dict[str, object]) -> int:
    return decode_page_cursor(cursor, key=key, **context) if cursor else 1


def _page_payload(
    *, items: list[dict[str, object]], next_cursor: str | None, total: int | None
) -> dict[str, object]:
    return {
        "metadataSynced": True,
        "live": True,
        "items": items,
        "nextCursor": next_cursor,
        "total": total,
        "guide": None,
    }


async def list_repositories(
    binding_id: str, *, search: str | None, limit: int, cursor: str | None
) -> dict[str, object]:
    cleaned = validate_search(search)
    live = await load_live_binding(binding_id)
    context = _cursor_context(live, live.ref, search=cleaned)
    key = repo_cursor_key()
    page = _decode_page(cursor, key, context)
    if not live.metadata_synced:
        return _empty_payload()

    async with open_provider(live) as provider:
        result = await run_provider_call(
            live,
            lambda: provider.list_repositories(
                search=cleaned, cursor=str(page), limit=limit
            ),
        )
    return _page_payload(
        items=[serialize_repository(item) for item in result.items],
        next_cursor=(
            encode_page_cursor(key=key, page=page + 1, **context)
            if result.next_cursor
            else None
        ),
        total=result.total,
    )


async def list_branches(
    binding_id: str,
    *,
    repo_id: str | None,
    search: str | None,
    limit: int,
    cursor: str | None,
) -> dict[str, object]:
    cleaned = validate_search(search)
    live = await load_live_binding(binding_id)
    selected = select_repository(live, repo_id)
    context = _cursor_context(live, selected, search=cleaned)
    key = repo_cursor_key()
    page = _decode_page(cursor, key, context)
    if not live.metadata_synced:
        return _empty_payload()

    async with open_provider(live) as provider:
        result = await run_provider_call(
            live,
            lambda: provider.list_branches(
                selected,
                search=cleaned,
                cursor=str(page),
                limit=limit,
            ),
        )
    return _page_payload(
        items=[serialize_branch(item) for item in result.items],
        next_cursor=(
            encode_page_cursor(key=key, page=page + 1, **context)
            if result.next_cursor
            else None
        ),
        total=result.total,
    )


async def list_commits(
    binding_id: str,
    *,
    repo_id: str | None,
    ref: str,
    limit: int,
    cursor: str | None,
) -> dict[str, object]:
    validate_ref(ref)
    live = await load_live_binding(binding_id)
    selected = select_repository(live, repo_id)
    context = _cursor_context(live, selected, ref=ref)
    key = repo_cursor_key()
    page = _decode_page(cursor, key, context)
    if not live.metadata_synced:
        return _empty_payload()

    async with open_provider(live) as provider:
        result = await run_provider_call(
            live,
            lambda: provider.list_commits(
                selected, ref=ref, cursor=str(page), limit=limit
            ),
        )
    return _page_payload(
        items=[serialize_commit(item) for item in result.items],
        next_cursor=(
            encode_page_cursor(key=key, page=page + 1, **context)
            if result.next_cursor
            else None
        ),
        total=result.total,
    )


def _slice_tree(
    entries: tuple[TreeEntry, ...], *, page: int, limit: int
) -> tuple[tuple[TreeEntry, ...], bool]:
    start = (page - 1) * limit
    return entries[start : start + limit], start + limit < len(entries)


async def list_tree(
    binding_id: str,
    *,
    repo_id: str | None,
    ref: str,
    path: str = "",
    limit: int,
    cursor: str | None,
) -> dict[str, object]:
    """逐级列出直接子项。

    云效 ``ListFiles`` 与 GitHub ``contents`` 都没有供应商侧分页；适配器一次
    返回当前目录的直接子项，服务层按 ``limit`` 切片并产出 ``hasMore``。
    ``truncated`` 只来自供应商的不完整信号，两者不互相冒充。
    """
    validate_ref(ref)
    if path:
        validate_repo_path(path)
    live = await load_live_binding(binding_id)
    selected = select_repository(live, repo_id)
    context = _cursor_context(live, selected, ref=ref, path=path)
    key = repo_cursor_key()
    page = _decode_page(cursor, key, context)
    if not live.metadata_synced:
        return _empty_payload(path=path, ref=ref)

    async with open_provider(live) as provider:
        tree = await run_provider_call(
            live,
            lambda: provider.list_tree(
                selected, ref=ref, path=path, cursor=None, limit=limit
            ),
        )
    entries, has_more = _slice_tree(tree.entries, page=page, limit=limit)
    return {
        "metadataSynced": True,
        "live": True,
        "path": path,
        "ref": ref,
        "items": [serialize_tree_entry(item) for item in entries],
        "truncated": tree.truncated,
        "hasMore": has_more,
        "nextCursor": (
            encode_page_cursor(key=key, page=page + 1, **context)
            if has_more
            else None
        ),
        "total": len(tree.entries),
        "guide": None,
    }


async def read_baseline(binding_id: str) -> dict[str, object]:
    """按 bindingId 读最近一次成功同步的快照；解绑或令牌失效仍可读。"""
    async with get_sessionmaker()() as db:
        row = await require_binding(db, binding_id)
        snapshots = await RepoRepository(db).load_baseline(binding_id)
        return serialize_baseline_document(row, snapshots)


__all__ = [
    "list_branches",
    "list_commits",
    "list_repositories",
    "list_tree",
    "read_baseline",
]
