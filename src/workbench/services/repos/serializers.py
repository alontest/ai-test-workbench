"""绑定、同步记录与基线快照的对外序列化；密文永不出口。"""

from __future__ import annotations

from collections.abc import Sequence

from workbench.api.serialization import to_rfc3339
from workbench.db.models import (
    RepoBinding,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)
from workbench.repos.types import (
    BranchSummary,
    CommitSummary,
    FileContent,
    RepositorySummary,
    TreeEntry,
)


def serialize_baseline(
    snapshot: RepoMetadataSnapshot | None,
) -> dict[str, object] | None:
    if snapshot is None:
        return None
    payload = snapshot.payload or {}
    return {
        "ref": snapshot.ref,
        "sha": payload.get("sha") or payload.get("headSha"),
        "fetchedAt": to_rfc3339(snapshot.fetched_at),
    }


def serialize_binding(
    row: RepoBinding,
    *,
    baseline: RepoMetadataSnapshot | None = None,
) -> dict[str, object]:
    return {
        "bindingId": row.binding_id,
        "projectId": row.project_id,
        "provider": row.provider,
        "apiBaseUrl": row.api_base_url,
        "orgId": row.org_id,
        "owner": row.owner,
        "repoId": row.repo_id,
        "repoName": row.repo_name,
        "displayName": row.display_name,
        "defaultBranch": row.default_branch,
        "tokenMasked": row.token_masked or "",
        "tokenExpiresAt": to_rfc3339(row.token_expires_at),
        "status": row.status,
        "lastVerifiedAt": to_rfc3339(row.last_verified_at),
        "lastVerifyResult": row.last_verify_result,
        "lastVerifyMessage": row.last_verify_message,
        "lastSyncAttemptAt": to_rfc3339(row.last_sync_attempt_at),
        "lastSyncStatus": row.last_sync_status,
        "lastSyncSuccessAt": to_rfc3339(row.last_sync_success_at),
        "lastSyncDurationMs": row.last_sync_duration_ms,
        "lastSyncErrorCategory": row.last_sync_error_category,
        "lastSyncErrorMessage": row.last_sync_error_message,
        "lastSyncRetryAfter": to_rfc3339(row.last_sync_retry_after),
        "baseline": serialize_baseline(baseline),
        "revokedAt": to_rfc3339(row.revoked_at),
        "createdAt": to_rfc3339(row.created_at),
        "updatedAt": to_rfc3339(row.updated_at),
    }


def serialize_sync_record(record: RepoSyncRecord) -> dict[str, object]:
    return {
        "syncId": record.sync_id,
        "bindingId": record.binding_id,
        "startedAt": to_rfc3339(record.started_at),
        "finishedAt": to_rfc3339(record.finished_at),
        "status": record.status,
        "durationMs": record.duration_ms,
        "repoCount": record.repo_count,
        "branchCount": record.branch_count,
        "commitCount": record.commit_count,
        "errorCategory": record.error_category,
        "errorMessage": record.error_message,
        "retryAfterAt": to_rfc3339(record.retry_after_at),
    }


def serialize_sync_binding(
    row: RepoBinding, snapshot: RepoMetadataSnapshot | None
) -> dict[str, object]:
    """端点 7 的绑定摘要；字段集按 api-spec 收窄，不返回令牌或密文。"""
    return {
        "bindingId": row.binding_id,
        "status": row.status,
        "lastSyncSuccessAt": to_rfc3339(row.last_sync_success_at),
        "baseline": serialize_baseline(snapshot),
    }


def _branch_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "name": payload.get("name"),
        "isDefault": bool(payload.get("isDefault")),
        "headSha": payload.get("headSha"),
        "committedAt": payload.get("committedAt"),
    }


def _commit_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "sha": payload.get("sha"),
        "shortSha": payload.get("shortSha"),
        "title": payload.get("title"),
        "authorName": payload.get("authorName"),
        "committedAt": payload.get("committedAt"),
    }


def _repo_payload(payload: dict[str, object]) -> dict[str, object]:
    return {
        "repoId": payload.get("repoId"),
        "fullName": payload.get("fullName"),
        "defaultBranch": payload.get("defaultBranch"),
    }


def serialize_baseline_document(
    row: RepoBinding, snapshots: Sequence[RepoMetadataSnapshot]
) -> dict[str, object]:
    """跨域只读基线：只读快照，不发供应商请求；解绑后仍可读。"""
    by_kind: dict[str, list[RepoMetadataSnapshot]] = {}
    for snapshot in snapshots:
        by_kind.setdefault(snapshot.kind, []).append(snapshot)
    repo_row = next(iter(by_kind.get("repo", ())), None)
    fetched_at = repo_row.fetched_at if repo_row is not None else None
    return {
        "bindingId": row.binding_id,
        "provider": row.provider,
        "repoName": row.repo_name,
        "status": row.status,
        "revoked": row.status == "revoked",
        "metadataSynced": repo_row is not None,
        "lastSyncSuccessAt": to_rfc3339(row.last_sync_success_at),
        "repo": _repo_payload(repo_row.payload or {}) if repo_row else None,
        "branches": [
            _branch_payload(item.payload or {})
            for item in by_kind.get("branch", ())
        ],
        "commits": [
            _commit_payload(item.payload or {})
            for item in by_kind.get("commit", ())
        ],
        "fetchedAt": to_rfc3339(fetched_at),
        "guide": None if repo_row is not None else "sync_first",
    }


def serialize_repository(item: RepositorySummary) -> dict[str, object]:
    return {
        "repoId": item.repo_id,
        "fullName": item.full_name,
        "displayName": item.display_name,
        "defaultBranch": item.default_branch,
        "webUrl": item.web_url,
    }


def serialize_branch(item: BranchSummary) -> dict[str, object]:
    return {
        "name": item.name,
        "isDefault": item.is_default,
        "headSha": item.head_sha,
        "committedAt": to_rfc3339(item.committed_at),
    }


def serialize_commit(item: CommitSummary) -> dict[str, object]:
    return {
        "sha": item.sha,
        "shortSha": item.short_sha,
        "title": item.title,
        "authorName": item.author_name,
        "committedAt": to_rfc3339(item.committed_at),
    }


def serialize_tree_entry(item: TreeEntry) -> dict[str, object]:
    return {
        "name": item.name,
        "path": item.path,
        "type": item.type,
        "sizeBytes": item.size_bytes,
    }


def serialize_file(content: FileContent, *, fetched_at: str | None) -> dict[str, object]:
    """成功读取的响应；``encoding`` 固定 ``text``，内容已解码为 UTF-8。"""
    return {
        "path": content.path,
        "ref": content.ref,
        "sizeBytes": content.size_bytes,
        "encoding": "text",
        "content": content.content,
        "fetchedAt": fetched_at,
    }


__all__ = [
    "serialize_baseline",
    "serialize_baseline_document",
    "serialize_binding",
    "serialize_branch",
    "serialize_commit",
    "serialize_file",
    "serialize_repository",
    "serialize_sync_binding",
    "serialize_sync_record",
    "serialize_tree_entry",
]
