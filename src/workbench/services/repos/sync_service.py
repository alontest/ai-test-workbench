"""手动同步：claim → 拉取 → 单事务覆盖快照 → 记录成功/失败（ADR-207 / ADR-211）。

失败是已完成的业务结果：不抛 502，写 ``failed`` 记录并保留旧快照与
``lastSyncSuccessAt``。并发只允许一个同步：进程内 per-binding 锁快速失败，
数据库 claim 兜住跨进程与重启。
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from workbench.api.serialization import to_rfc3339
from workbench.core.crypto import CredentialUnavailable
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.models import RepoBinding, RepoSyncRecord
from workbench.db.repositories.repos import RepoRepository, SnapshotRow
from workbench.repos.constants import (
    REPO_COMMIT_LIMIT,
    REPO_PAGE_MAX,
    REPO_SYNC_BUDGET_SECONDS,
    REPO_SYNC_LOCK_TTL_SECONDS,
    REPO_SYNC_MAX_PAGES,
)
from workbench.repos.crypto import decrypt_token
from workbench.repos.cursor import decode_page_cursor, encode_page_cursor
from workbench.repos.errors import RepoConcurrencyError, RepoDomainError
from workbench.repos.providers import build_provider
from workbench.repos.providers.base import repository_ref
from workbench.repos.redaction import safe_log_fields
from workbench.repos.types import (
    BranchSummary,
    CommitSummary,
    ProviderError,
    RepoProvider,
    RepositoryRef,
    RepositorySummary,
)
from workbench.services.repos.binding_service import (
    REVOKED_MESSAGE,
    repo_cursor_key,
    repo_token_key,
    require_binding,
)
from workbench.services.repos.serializers import (
    serialize_sync_binding,
    serialize_sync_record,
)

logger = logging.getLogger(__name__)

IN_PROGRESS_MESSAGE = "该绑定正在同步，请稍后重试。"
BUDGET_MESSAGE = "同步超出时间预算。"
BRANCH_LIMIT_MESSAGE = "分支数量超过同步上限。"
INTERRUPTED_MESSAGE = "同步被中断。"
CREDENTIAL_MESSAGE = "仓库令牌不可用。"

_CATEGORY_BY_PROVIDER = {
    "auth": "auth",
    "permission_denied": "permission",
    "not_found": "permission",
    "rate_limited": "rate_limit",
    "network": "network",
    "timeout": "network",
    "server_error": "other",
    "invalid_response": "other",
}

_sync_locks: dict[str, asyncio.Lock] = {}


@dataclass(frozen=True)
class _Fetched:
    repo: RepositorySummary
    branches: tuple[BranchSummary, ...]
    commits: tuple[CommitSummary, ...]


class _SyncFailure(Exception):
    def __init__(
        self,
        category: str,
        message: str,
        *,
        retry_after_at: datetime | None = None,
    ) -> None:
        self.category = category
        self.message = message
        self.retry_after_at = retry_after_at
        super().__init__(message)


def _lock_for(binding_id: str) -> asyncio.Lock:
    lock = _sync_locks.get(binding_id)
    if lock is None:
        lock = asyncio.Lock()
        _sync_locks[binding_id] = lock
    return lock


def _in_progress() -> RepoConcurrencyError:
    return RepoConcurrencyError("sync_in_progress", IN_PROGRESS_MESSAGE)


def _elapsed_ms(started_at: datetime, finished_at: datetime) -> int:
    return max(0, int((finished_at - started_at).total_seconds() * 1000))


async def claim_and_start(
    binding_id: str, *, now: datetime
) -> tuple[str, RepositoryRef, str | None]:
    """数据库原子 claim + 新 running 记录。

    claim 成功即说明此前的 claim 已释放或过期，因此该绑定遗留的 ``running``
    记录一律归并为 ``failed(interrupted)``。
    """
    async with get_sessionmaker()() as db:
        row = await require_binding(db, binding_id)
        if row.status == "revoked":
            raise RepoDomainError("binding_revoked", REVOKED_MESSAGE, status_code=409)
        repo = RepoRepository(db)
        claimed = await repo.claim_sync(
            binding_id, now=now, ttl_seconds=REPO_SYNC_LOCK_TTL_SECONDS
        )
        if not claimed:
            raise _in_progress()
        interrupted = await repo.interrupt_running_records(
            binding_id, now=now, message=INTERRUPTED_MESSAGE
        )
        record = RepoSyncRecord(
            binding_id=binding_id,
            started_at=now,
            status="running",
            repo_count=0,
            branch_count=0,
            commit_count=0,
            created_at=now,
        )
        await repo.add_sync_record(record)
        await db.commit()
        if interrupted:
            logger.info(
                "repo sync reclaimed %s",
                safe_log_fields(
                    {"bindingId": binding_id, "provider": row.provider}
                ),
            )
        return record.sync_id, repository_ref(row), row.token_ciphertext


async def _fetch_branches(
    provider: RepoProvider, repo: RepositoryRef
) -> tuple[BranchSummary, ...]:
    collected: list[BranchSummary] = []
    cursor: str | None = None
    for _ in range(REPO_SYNC_MAX_PAGES):
        page = await provider.list_branches(
            repo, search=None, cursor=cursor, limit=REPO_PAGE_MAX
        )
        collected.extend(page.items)
        cursor = page.next_cursor
        if cursor is None:
            return tuple(collected)
    raise _SyncFailure("other", BRANCH_LIMIT_MESSAGE)


async def _fetch_commits(
    provider: RepoProvider, repo: RepositoryRef, default_branch: str | None
) -> tuple[CommitSummary, ...]:
    if not default_branch:
        return ()
    page = await provider.list_commits(
        repo, ref=default_branch, cursor=None, limit=REPO_COMMIT_LIMIT
    )
    return tuple(page.items[:REPO_COMMIT_LIMIT])


async def fetch_snapshot(
    repo: RepositoryRef, token: str, *, budget_seconds: float
) -> _Fetched:
    provider = build_provider(repo, token)
    try:
        async with asyncio.timeout(budget_seconds):
            summary = await provider.get_repository(repo)
            branches = await _fetch_branches(provider, repo)
            commits = await _fetch_commits(
                provider, repo, summary.default_branch or repo.default_branch
            )
    except ProviderError as exc:
        raise _SyncFailure(
            _CATEGORY_BY_PROVIDER[exc.category],
            exc.message,
            retry_after_at=exc.retry_after_at,
        ) from None
    except TimeoutError:
        raise _SyncFailure("other", BUDGET_MESSAGE) from None
    finally:
        await provider.aclose()
    return _Fetched(repo=summary, branches=branches, commits=commits)


def _snapshot_rows(
    fetched: _Fetched, *, default_branch: str | None
) -> tuple[SnapshotRow, tuple[SnapshotRow, ...], tuple[SnapshotRow, ...]]:
    """把归一化 DTO 落成快照 payload；只存元数据，不含正文与供应商原文。

    ``isDefault`` 以本次同步拿到的仓库默认分支为准；适配器侧
    ``ref.default_branch`` 在首次同步前可能为空，不能直接采信。
    """
    default_sha = next(
        (
            branch.head_sha
            for branch in fetched.branches
            if default_branch is not None
            and branch.name == default_branch
            and branch.head_sha
        ),
        None,
    )
    if default_sha is None:
        default_sha = next(
            (
                branch.head_sha
                for branch in fetched.branches
                if branch.is_default and branch.head_sha
            ),
            None,
        )
    if default_sha is None and fetched.commits:
        default_sha = fetched.commits[0].sha

    repo_id = fetched.repo.repo_id
    repo_row = SnapshotRow(
        repo_id=repo_id,
        ref=default_branch,
        payload={
            "repoId": repo_id,
            "fullName": fetched.repo.full_name,
            "displayName": fetched.repo.display_name,
            "defaultBranch": fetched.repo.default_branch,
            "webUrl": fetched.repo.web_url,
            "sha": default_sha,
        },
    )
    branch_rows = tuple(
        SnapshotRow(
            repo_id=repo_id,
            ref=branch.name,
            payload={
                "name": branch.name,
                "isDefault": (
                    branch.name == default_branch
                    if default_branch is not None
                    else branch.is_default
                ),
                "headSha": branch.head_sha,
                "committedAt": to_rfc3339(branch.committed_at),
            },
        )
        for branch in fetched.branches
    )
    commit_rows = tuple(
        SnapshotRow(
            repo_id=repo_id,
            ref=default_branch,
            payload={
                "sha": commit.sha,
                "shortSha": commit.short_sha,
                "title": commit.title,
                "authorName": commit.author_name,
                "committedAt": to_rfc3339(commit.committed_at),
            },
        )
        for commit in fetched.commits
    )
    return repo_row, branch_rows, commit_rows


async def persist_success(
    binding_id: str,
    sync_id: str,
    fetched: _Fetched,
    *,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    async with get_sessionmaker()() as db:
        row = await require_binding(db, binding_id)
        record = await _record(db, sync_id)
        if row.status == "revoked":
            _finish_failed(record, "other", REVOKED_MESSAGE, started_at, finished_at)
            await db.commit()
            return
        default_branch = fetched.repo.default_branch or row.default_branch
        repo_row, branch_rows, commit_rows = _snapshot_rows(
            fetched, default_branch=default_branch
        )
        await RepoRepository(db).replace_snapshot(
            binding_id,
            repo=repo_row,
            branches=branch_rows,
            commits=commit_rows,
            fetched_at=finished_at,
        )
        duration = _elapsed_ms(started_at, finished_at)
        _finish_success(
            record,
            repo_count=1,
            branch_count=len(branch_rows),
            commit_count=len(commit_rows),
            finished_at=finished_at,
            duration=duration,
        )
        row.status = "connected"
        row.default_branch = default_branch
        _apply_binding_success(row, started_at, finished_at, duration)
        await db.commit()


async def persist_failure(
    binding_id: str,
    sync_id: str,
    failure: _SyncFailure,
    *,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    async with get_sessionmaker()() as db:
        row = await require_binding(db, binding_id)
        record = await _record(db, sync_id)
        _finish_failed(
            record,
            failure.category,
            failure.message,
            started_at,
            finished_at,
            retry_after_at=failure.retry_after_at,
        )
        if row.status != "revoked":
            _apply_binding_failure(row, failure, started_at, finished_at)
        await db.commit()


async def _record(db, sync_id: str) -> RepoSyncRecord:  # noqa: ANN001
    record = await db.get(RepoSyncRecord, sync_id)
    if record is None:
        raise RepoDomainError(
            "internal_error", "服务器内部错误。", status_code=500
        )
    return record


def _finish_success(
    record: RepoSyncRecord,
    *,
    repo_count: int,
    branch_count: int,
    commit_count: int,
    finished_at: datetime,
    duration: int,
) -> None:
    record.status = "success"
    record.finished_at = finished_at
    record.duration_ms = duration
    record.repo_count = repo_count
    record.branch_count = branch_count
    record.commit_count = commit_count
    record.error_category = None
    record.error_message = None
    record.retry_after_at = None


def _finish_failed(
    record: RepoSyncRecord,
    category: str,
    message: str,
    started_at: datetime,
    finished_at: datetime,
    *,
    retry_after_at: datetime | None = None,
) -> None:
    record.status = "failed"
    record.finished_at = finished_at
    record.duration_ms = _elapsed_ms(started_at, finished_at)
    record.repo_count = 0
    record.branch_count = 0
    record.commit_count = 0
    record.error_category = category
    record.error_message = message
    record.retry_after_at = retry_after_at


def _apply_binding_success(
    row: RepoBinding,
    started_at: datetime,
    finished_at: datetime,
    duration: int,
) -> None:
    row.last_sync_attempt_at = started_at
    row.last_sync_status = "success"
    row.last_sync_success_at = finished_at
    row.last_sync_duration_ms = duration
    row.last_sync_error_category = None
    row.last_sync_error_message = None
    row.last_sync_retry_after = None
    row.sync_started_at = None
    row.updated_at = finished_at


def _apply_binding_failure(
    row: RepoBinding,
    failure: _SyncFailure,
    started_at: datetime,
    finished_at: datetime,
) -> None:
    row.last_sync_attempt_at = started_at
    row.last_sync_status = "failed"
    row.last_sync_error_category = failure.category
    row.last_sync_error_message = failure.message
    row.last_sync_retry_after = failure.retry_after_at
    row.sync_started_at = None
    if failure.category in ("auth", "permission"):
        row.status = "token_invalid"
    row.updated_at = finished_at


async def _result(binding_id: str, sync_id: str) -> dict[str, object]:
    async with get_sessionmaker()() as db:
        repo = RepoRepository(db)
        row = await repo.get(binding_id)
        if row is None:
            raise RepoDomainError(
                "binding_not_found", "仓库绑定不存在。", status_code=404
            )
        record = await _record(db, sync_id)
        snapshot = (await repo.latest_repo_snapshots([binding_id])).get(binding_id)
        return {
            "record": serialize_sync_record(record),
            "binding": serialize_sync_binding(row, snapshot),
        }


async def sync_binding(
    binding_id: str,
    *,
    budget_seconds: float = REPO_SYNC_BUDGET_SECONDS,
    now: datetime | None = None,
) -> dict[str, object]:
    lock = _lock_for(binding_id)
    if lock.locked():
        raise _in_progress()
    async with lock:
        started_at = now or utcnow()
        sync_id, repo, ciphertext = await claim_and_start(binding_id, now=started_at)
        logger.info(
            "repo sync started %s",
            safe_log_fields({"bindingId": binding_id, "provider": repo.provider}),
        )
        try:
            token = decrypt_token(ciphertext, key=repo_token_key())
            fetched = await fetch_snapshot(
                repo, token, budget_seconds=budget_seconds
            )
        except CredentialUnavailable:
            failure: _SyncFailure | None = _SyncFailure("auth", CREDENTIAL_MESSAGE)
        except _SyncFailure as exc:
            failure = exc
        else:
            failure = None
        finished_at = utcnow()
        if failure is None:
            await persist_success(
                binding_id,
                sync_id,
                fetched,
                started_at=started_at,
                finished_at=finished_at,
            )
        else:
            await persist_failure(
                binding_id,
                sync_id,
                failure,
                started_at=started_at,
                finished_at=finished_at,
            )
        logger.info(
            "repo sync finished %s",
            safe_log_fields(
                {
                    "bindingId": binding_id,
                    "provider": repo.provider,
                    "category": failure.category if failure else None,
                }
            ),
        )
        return await _result(binding_id, sync_id)


async def list_sync_records(
    binding_id: str, *, limit: int, cursor: str | None
) -> tuple[list[dict[str, object]], str | None]:
    key = repo_cursor_key()
    async with get_sessionmaker()() as db:
        row = await require_binding(db, binding_id)
        context = {
            "binding_id": binding_id,
            "provider": row.provider,
            "repo_key": row.repo_key,
        }
        page = decode_page_cursor(cursor, key=key, **context) if cursor else 1
        rows = await RepoRepository(db).list_sync_records(
            binding_id, limit=limit + 1, offset=(page - 1) * limit
        )
    page_rows = rows[:limit]
    has_more = len(rows) > limit
    next_cursor = None
    if has_more and page_rows:
        next_cursor = encode_page_cursor(key=key, page=page + 1, **context)
    return [serialize_sync_record(record) for record in page_rows], next_cursor


__all__ = ["list_sync_records", "sync_binding"]
