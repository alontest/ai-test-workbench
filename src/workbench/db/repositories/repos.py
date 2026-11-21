"""仓库集成仓储：绑定、同步 claim、快照覆盖、记录分页与基线读取。

方法只改当前 ``AsyncSession`` 的挂起事务，不自行 commit；调用方决定事务边界。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.db.base import utcnow
from workbench.db.models import (
    RepoBinding,
    RepoFileReadRecord,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)

SNAPSHOT_KINDS = ("repo", "branch", "commit", "tree")
BASELINE_KINDS = ("repo", "branch", "commit")


@dataclass(frozen=True)
class SnapshotRow:
    """由同步服务归一化后的单行元数据；不含供应商原始 JSON 与文件正文。"""

    repo_id: str
    ref: str | None
    payload: Mapping[str, object]
    truncated: bool = False


class RepoRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, binding_id: str) -> RepoBinding | None:
        return await self.db.get(RepoBinding, binding_id)

    async def add_binding(self, binding: RepoBinding) -> RepoBinding:
        self.db.add(binding)
        await self.db.flush()
        return binding

    async def find_active(
        self, *, project_id: int, provider: str, repo_key: str
    ) -> RepoBinding | None:
        return await self.db.scalar(
            select(RepoBinding).where(
                RepoBinding.project_id == project_id,
                RepoBinding.provider == provider,
                RepoBinding.repo_key == repo_key,
                RepoBinding.active_flag == "1",
            )
        )

    async def list_for_project(
        self,
        project_id: int,
        *,
        limit: int,
        offset: int = 0,
        before: tuple[datetime, str] | None = None,
    ) -> list[RepoBinding]:
        statement = select(RepoBinding).where(RepoBinding.project_id == project_id)
        if before is not None:
            moment, binding_id = before
            statement = statement.where(
                or_(
                    RepoBinding.created_at < moment,
                    and_(
                        RepoBinding.created_at == moment,
                        RepoBinding.binding_id < binding_id,
                    ),
                )
            )
        statement = statement.order_by(
            RepoBinding.created_at.desc(), RepoBinding.binding_id.desc()
        ).offset(offset).limit(limit)
        return list(await self.db.scalars(statement))

    async def latest_repo_snapshots(
        self, binding_ids: Sequence[str]
    ) -> dict[str, RepoMetadataSnapshot]:
        """一次查询取每个绑定最新的 ``kind='repo'`` 快照行；无输入返回空字典。"""
        if not binding_ids:
            return {}
        rows = await self.db.scalars(
            select(RepoMetadataSnapshot)
            .where(
                RepoMetadataSnapshot.binding_id.in_(list(binding_ids)),
                RepoMetadataSnapshot.kind == "repo",
            )
            .order_by(
                RepoMetadataSnapshot.fetched_at.desc(),
                RepoMetadataSnapshot.snapshot_id.desc(),
            )
        )
        latest: dict[str, RepoMetadataSnapshot] = {}
        for row in rows:
            latest.setdefault(row.binding_id, row)
        return latest

    async def update_token(
        self,
        binding_id: str,
        *,
        ciphertext: str,
        masked: str,
        now: datetime | None = None,
    ) -> bool:
        """只替换密文、掩码与 updated_at（AC-017-4 / AC-023-2）。"""
        result = await self.db.execute(
            update(RepoBinding)
            .where(RepoBinding.binding_id == binding_id)
            .values(
                token_ciphertext=ciphertext,
                token_masked=masked,
                updated_at=now or utcnow(),
            )
            .execution_options(synchronize_session="evaluate")
        )
        return (result.rowcount or 0) == 1

    async def unbind(self, binding_id: str, *, now: datetime | None = None) -> bool:
        """解绑不删行：revoked + 清空密文与掩码 + active_flag=NULL。"""
        moment = now or utcnow()
        result = await self.db.execute(
            update(RepoBinding)
            .where(RepoBinding.binding_id == binding_id)
            .values(
                status="revoked",
                active_flag=None,
                token_ciphertext=None,
                token_masked=None,
                revoked_at=moment,
                updated_at=moment,
                sync_started_at=None,
            )
            .execution_options(synchronize_session="evaluate")
        )
        return (result.rowcount or 0) == 1

    async def claim_sync(
        self,
        binding_id: str,
        *,
        now: datetime,
        ttl_seconds: int,
    ) -> bool:
        """数据库原子 claim；返回 False 表示已有未过期 claim 或已解绑。"""
        cutoff = now - timedelta(seconds=ttl_seconds)
        result = await self.db.execute(
            update(RepoBinding)
            .where(
                RepoBinding.binding_id == binding_id,
                RepoBinding.status != "revoked",
                or_(
                    RepoBinding.sync_started_at.is_(None),
                    RepoBinding.sync_started_at < cutoff,
                ),
            )
            .values(sync_started_at=now, updated_at=now)
            .execution_options(synchronize_session="evaluate")
        )
        return (result.rowcount or 0) == 1

    async def release_sync_claim(
        self, binding_id: str, *, now: datetime | None = None
    ) -> None:
        await self.db.execute(
            update(RepoBinding)
            .where(RepoBinding.binding_id == binding_id)
            .values(sync_started_at=None, updated_at=now or utcnow())
            .execution_options(synchronize_session="evaluate")
        )

    async def replace_snapshot(
        self,
        binding_id: str,
        *,
        repo: SnapshotRow | None,
        branches: Sequence[SnapshotRow],
        commits: Sequence[SnapshotRow],
        fetched_at: datetime,
    ) -> None:
        """删除该绑定旧的 repo/branch/commit 快照并插入新行（同一事务）。"""
        await self.db.execute(
            delete(RepoMetadataSnapshot)
            .where(
                RepoMetadataSnapshot.binding_id == binding_id,
                RepoMetadataSnapshot.kind.in_(BASELINE_KINDS),
            )
            .execution_options(synchronize_session=False)
        )
        rows: list[RepoMetadataSnapshot] = []
        if repo is not None:
            rows.append(
                self._snapshot_row(binding_id, "repo", repo, fetched_at)
            )
        rows.extend(
            self._snapshot_row(binding_id, "branch", row, fetched_at)
            for row in branches
        )
        rows.extend(
            self._snapshot_row(binding_id, "commit", row, fetched_at)
            for row in commits
        )
        self.db.add_all(rows)

    @staticmethod
    def _snapshot_row(
        binding_id: str,
        kind: str,
        row: SnapshotRow,
        fetched_at: datetime,
    ) -> RepoMetadataSnapshot:
        return RepoMetadataSnapshot(
            snapshot_id=uuid4().hex,
            binding_id=binding_id,
            repo_id=row.repo_id,
            kind=kind,
            ref=row.ref,
            payload=dict(row.payload),
            fetched_at=fetched_at,
            truncated=row.truncated,
        )

    async def load_baseline(
        self, binding_id: str
    ) -> list[RepoMetadataSnapshot]:
        """取该绑定最近一次快照批次的 repo/branch/commit 行；没有则空列表。"""
        moment = await self.db.scalar(
            select(func.max(RepoMetadataSnapshot.fetched_at)).where(
                RepoMetadataSnapshot.binding_id == binding_id,
                RepoMetadataSnapshot.kind.in_(BASELINE_KINDS),
            )
        )
        if moment is None:
            return []
        rows = await self.db.scalars(
            select(RepoMetadataSnapshot)
            .where(
                RepoMetadataSnapshot.binding_id == binding_id,
                RepoMetadataSnapshot.fetched_at == moment,
                RepoMetadataSnapshot.kind.in_(BASELINE_KINDS),
            )
            .order_by(
                RepoMetadataSnapshot.kind.asc(),
                RepoMetadataSnapshot.ref.asc(),
                RepoMetadataSnapshot.snapshot_id.asc(),
            )
        )
        return list(rows)

    async def add_sync_record(self, record: RepoSyncRecord) -> RepoSyncRecord:
        self.db.add(record)
        await self.db.flush()
        return record

    async def list_sync_records(
        self,
        binding_id: str,
        *,
        limit: int,
        offset: int = 0,
        before: tuple[datetime, str] | None = None,
    ) -> list[RepoSyncRecord]:
        statement = select(RepoSyncRecord).where(
            RepoSyncRecord.binding_id == binding_id
        )
        if before is not None:
            moment, sync_id = before
            statement = statement.where(
                or_(
                    RepoSyncRecord.started_at < moment,
                    and_(
                        RepoSyncRecord.started_at == moment,
                        RepoSyncRecord.sync_id < sync_id,
                    ),
                )
            )
        statement = (
            statement.order_by(
                RepoSyncRecord.started_at.desc(), RepoSyncRecord.sync_id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return list(await self.db.scalars(statement))

    async def interrupt_running_records(
        self, binding_id: str, *, now: datetime, message: str
    ) -> int:
        """把该绑定遗留的 ``running`` 记录归并为 ``failed(interrupted)``。"""
        rows = await self.db.scalars(
            select(RepoSyncRecord).where(
                RepoSyncRecord.binding_id == binding_id,
                RepoSyncRecord.status == "running",
            )
        )
        count = 0
        for row in rows:
            row.status = "failed"
            row.error_category = "interrupted"
            row.error_message = message
            row.finished_at = now
            count += 1
        return count

    async def add_file_read_record(
        self, record: RepoFileReadRecord
    ) -> RepoFileReadRecord:
        self.db.add(record)
        await self.db.flush()
        return record


__all__ = ["BASELINE_KINDS", "RepoRepository", "SNAPSHOT_KINDS", "SnapshotRow"]
