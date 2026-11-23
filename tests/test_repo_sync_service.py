"""仓储层与同步服务：claim、快照覆盖、失败保留、reclaim、预算与基线读取。"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from vigil_workbench.config import get_settings
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import (
    ProjectContext,
    RepoBinding,
    RepoFileReadRecord,
    RepoMetadataSnapshot,
    RepoSyncRecord,
)
from vigil_workbench.db.repositories.repos import RepoRepository, SnapshotRow
from vigil_workbench.repos.crypto import encrypt_token
from vigil_workbench.repos.errors import RepoConcurrencyError
from vigil_workbench.repos.types import Page, RepositorySummary
from vigil_workbench.services.repos import browse_service, sync_service

TOKEN_COLUMNS = {"token_ciphertext", "token_masked", "updated_at"}


async def _project(db) -> ProjectContext:  # noqa: ANN001
    name = f"仓库仓储-{uuid.uuid4().hex}"
    project = ProjectContext(name=name, name_key=name)
    db.add(project)
    await db.flush()
    return project


def _binding(project_id: int, *, status: str = "connected") -> RepoBinding:
    now = utcnow()
    return RepoBinding(
        binding_id=uuid.uuid4().hex,
        project_id=project_id,
        provider="github",
        api_base_url="https://api.github.com",
        owner="pay",
        repo_id="pay/checkout",
        repo_name="pay/checkout",
        repo_key=f"github:pay/{uuid.uuid4().hex}",
        display_name="pay/checkout",
        default_branch="main",
        token_ciphertext="v1:old-nonce:old-cipher",
        token_masked="ghp_****fake",
        status=status,
        active_flag="1",
        last_sync_success_at=now,
        created_at=now,
        updated_at=now,
    )


async def test_tc204_update_token_touches_only_token_columns(database) -> None:  # noqa: ANN001
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _binding(project.project_id)
        db.add(binding)
        await db.flush()
        db.add(
            RepoSyncRecord(
                sync_id=uuid.uuid4().hex,
                binding_id=binding.binding_id,
                started_at=utcnow(),
                status="success",
                repo_count=1,
                created_at=utcnow(),
            )
        )
        db.add(
            RepoMetadataSnapshot(
                snapshot_id=uuid.uuid4().hex,
                binding_id=binding.binding_id,
                repo_id="pay/checkout",
                kind="repo",
                ref="main",
                payload={"fullName": "pay/checkout"},
                fetched_at=utcnow(),
                truncated=False,
            )
        )
        db.add(
            RepoFileReadRecord(
                read_id=uuid.uuid4().hex,
                binding_id=binding.binding_id,
                repo_id="pay/checkout",
                ref="main",
                file_path="src/main.py",
                byte_size=10,
                encoding="text",
                status="success",
                fetched_at=utcnow(),
            )
        )
        binding_id = binding.binding_id
        before = {
            column.name: getattr(binding, column.name)
            for column in RepoBinding.__table__.columns
            if column.name not in TOKEN_COLUMNS
        }
        await db.commit()

        repo = RepoRepository(db)
        later = utcnow() + timedelta(seconds=5)
        assert await repo.update_token(
            binding_id,
            ciphertext="v1:new-nonce:new-cipher",
            masked="ghp_****new2",
            now=later,
        )
        await db.commit()

        refreshed = await repo.get(binding_id)
        assert refreshed is not None
        await db.refresh(refreshed)
        assert refreshed.token_ciphertext == "v1:new-nonce:new-cipher"
        assert refreshed.token_masked == "ghp_****new2"
        assert refreshed.updated_at == later
        for column, value in before.items():
            assert getattr(refreshed, column) == value, column

        assert await db.scalar(select(func.count()).select_from(RepoSyncRecord)) == 1
        assert (
            await db.scalar(select(func.count()).select_from(RepoMetadataSnapshot))
            == 1
        )
        assert (
            await db.scalar(select(func.count()).select_from(RepoFileReadRecord))
            == 1
        )


async def test_tc217_claim_is_exclusive_and_reclaims_after_ttl(database) -> None:  # noqa: ANN001
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _binding(project.project_id)
        revoked = _binding(project.project_id, status="revoked")
        db.add_all([binding, revoked])
        binding_id = binding.binding_id
        revoked_id = revoked.binding_id
        await db.commit()

        repo = RepoRepository(db)
        now = utcnow()

        assert await repo.claim_sync(binding_id, now=now, ttl_seconds=900)
        await db.commit()
        assert not await repo.claim_sync(
            binding_id, now=now + timedelta(seconds=1), ttl_seconds=900
        )
        assert await repo.claim_sync(
            binding_id, now=now + timedelta(seconds=901), ttl_seconds=900
        )

        assert not await repo.claim_sync(revoked_id, now=now, ttl_seconds=900)
        assert not await repo.claim_sync(
            uuid.uuid4().hex, now=now, ttl_seconds=900
        )

        await repo.release_sync_claim(binding_id, now=now)
        await db.commit()
        released = await repo.get(binding_id)
        assert released is not None
        await db.refresh(released)
        assert released.sync_started_at is None


async def test_tc233_baseline_reads_latest_snapshot_and_survives_unbind(database) -> None:  # noqa: ANN001
    async with database.sessionmaker() as db:
        project = await _project(db)
        project_id = project.project_id
        binding = _binding(project_id)
        db.add(binding)
        binding_id = binding.binding_id
        repo_key = binding.repo_key
        success_at = binding.last_sync_success_at
        await db.commit()
        repo = RepoRepository(db)

        first = utcnow()
        await repo.replace_snapshot(
            binding_id,
            repo=SnapshotRow(
                repo_id="pay/checkout", ref="main", payload={"fullName": "pay/checkout"}
            ),
            branches=(
                SnapshotRow(repo_id="pay/checkout", ref="main", payload={"name": "main"}),
                SnapshotRow(repo_id="pay/checkout", ref="dev", payload={"name": "dev"}),
            ),
            commits=(
                SnapshotRow(
                    repo_id="pay/checkout", ref="main", payload={"sha": "a" * 40}
                ),
            ),
            fetched_at=first,
        )
        await db.commit()

        rows = await repo.load_baseline(binding_id)
        assert [row.kind for row in rows] == ["branch", "branch", "commit", "repo"]
        assert all(row.fetched_at == first for row in rows)

        second = first + timedelta(seconds=1)
        await repo.replace_snapshot(
            binding_id,
            repo=SnapshotRow(
                repo_id="pay/checkout",
                ref="dev",
                payload={"fullName": "pay/checkout"},
            ),
            branches=(
                SnapshotRow(repo_id="pay/checkout", ref="dev", payload={"name": "dev"}),
            ),
            commits=(),
            fetched_at=second,
        )
        await db.commit()

        refreshed_rows = await repo.load_baseline(binding_id)
        assert [row.kind for row in refreshed_rows] == ["branch", "repo"]
        assert all(row.fetched_at == second for row in refreshed_rows)

        await repo.unbind(binding_id, now=second)
        await db.commit()

        unbound = await repo.get(binding_id)
        assert unbound is not None
        await db.refresh(unbound)
        assert unbound.status == "revoked"
        assert unbound.active_flag is None
        assert unbound.token_ciphertext is None
        assert unbound.token_masked is None
        assert unbound.revoked_at == second
        assert unbound.last_sync_success_at == success_at

        assert len(await repo.load_baseline(binding_id)) == 2
        assert await repo.find_active(
            project_id=project_id,
            provider="github",
            repo_key=repo_key,
        ) is None


# --- 同步服务（TASK-RI-222 / 224 / 225）-------------------------------


GITHUB_REF = RepositorySummary(
    repo_id="pay/checkout",
    full_name="pay/checkout",
    display_name="checkout",
    default_branch="main",
    web_url="https://github.com/pay/checkout",
)


def _token_binding(project_id: int, *, token: str = "ghp_test_token") -> RepoBinding:
    binding = _binding(project_id)
    binding.token_ciphertext = encrypt_token(
        token, key=get_settings().repo_token_key_bytes
    )
    return binding


class _FakeProvider:
    def __init__(
        self,
        *,
        entered: asyncio.Event | None = None,
        release: asyncio.Event | None = None,
        delay: float = 0,
    ) -> None:
        self.entered = entered
        self.release = release
        self.delay = delay
        self.token_expires_at = None

    async def get_repository(self, repo):  # noqa: ANN001, ANN201
        if self.entered is not None:
            self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if self.delay:
            await asyncio.sleep(self.delay)
        return GITHUB_REF

    async def list_branches(self, repo, *, search, cursor, limit):  # noqa: ANN001, ANN201
        return Page(items=())

    async def list_commits(self, repo, *, ref, cursor, limit):  # noqa: ANN001, ANN201
        return Page(items=())

    async def aclose(self) -> None:
        return None


def _fake_factory(provider: _FakeProvider):  # noqa: ANN202
    def factory(ref, token_value, **kwargs):  # noqa: ANN001, ANN202
        return provider

    return factory


async def _count_records(database, binding_id: str) -> int:  # noqa: ANN001
    async with database.sessionmaker() as db:
        return (
            await db.scalar(
                select(func.count())
                .select_from(RepoSyncRecord)
                .where(RepoSyncRecord.binding_id == binding_id)
            )
        ) or 0


async def test_tc217_concurrent_sync_returns_409_without_second_record(
    database, monkeypatch
) -> None:
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _token_binding(project.project_id)
        db.add(binding)
        binding_id = binding.binding_id
        await db.commit()

    entered = asyncio.Event()
    release = asyncio.Event()
    provider = _FakeProvider(entered=entered, release=release)
    monkeypatch.setattr(sync_service, "build_provider", _fake_factory(provider))

    task = asyncio.create_task(sync_service.sync_binding(binding_id))
    await asyncio.wait_for(entered.wait(), timeout=2)

    with pytest.raises(RepoConcurrencyError) as info:
        await sync_service.sync_binding(binding_id)
    assert info.value.code == "sync_in_progress"

    release.set()
    result = await task

    assert result["record"]["status"] == "success"
    assert await _count_records(database, binding_id) == 1


async def test_tc218_stale_claim_reclaimed_and_marked_interrupted(
    database, monkeypatch, caplog
) -> None:
    stale_at = utcnow() - timedelta(minutes=20)
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _token_binding(project.project_id)
        binding.sync_started_at = stale_at
        db.add(binding)
        await db.flush()
        legacy = RepoSyncRecord(
            sync_id=uuid.uuid4().hex,
            binding_id=binding.binding_id,
            started_at=stale_at,
            status="running",
            repo_count=0,
            branch_count=0,
            commit_count=0,
            created_at=stale_at,
        )
        db.add(legacy)
        legacy_id = legacy.sync_id
        binding_id = binding.binding_id
        await db.commit()

    monkeypatch.setattr(
        sync_service,
        "build_provider",
        _fake_factory(_FakeProvider()),
    )
    with caplog.at_level(logging.INFO, logger="vigil_workbench"):
        result = await sync_service.sync_binding(binding_id)

    assert result["record"]["status"] == "success"
    async with database.sessionmaker() as db:
        reclaimed = await db.get(RepoSyncRecord, legacy_id)
        assert reclaimed is not None
        assert reclaimed.status == "failed"
        assert reclaimed.error_category == "interrupted"
        assert reclaimed.finished_at is not None
        row = await db.get(RepoBinding, binding_id)
        assert row is not None
        assert row.sync_started_at is None
    assert await _count_records(database, binding_id) == 2


async def test_tc223_sync_budget_aborts_without_partial_snapshot(
    database, monkeypatch
) -> None:
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _token_binding(project.project_id)
        db.add(binding)
        binding_id = binding.binding_id
        success_before = binding.last_sync_success_at
        await db.commit()

    slow = _FakeProvider(delay=5)
    monkeypatch.setattr(sync_service, "build_provider", _fake_factory(slow))

    result = await sync_service.sync_binding(binding_id, budget_seconds=0.05)

    assert result["record"]["status"] == "failed"
    assert result["record"]["errorCategory"] == "other"
    assert result["record"]["errorMessage"] == sync_service.BUDGET_MESSAGE
    async with database.sessionmaker() as db:
        snapshots = list(
            await db.scalars(
                select(RepoMetadataSnapshot).where(
                    RepoMetadataSnapshot.binding_id == binding_id
                )
            )
        )
        assert snapshots == []
        row = await db.get(RepoBinding, binding_id)
        assert row is not None
        assert row.last_sync_success_at == success_before
        assert row.sync_started_at is None


async def test_tc233_baseline_service_reads_snapshot_without_provider(
    database, monkeypatch
) -> None:
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _binding(project.project_id)
        db.add(binding)
        binding_id = binding.binding_id
        await db.commit()
        fetched_at = utcnow()
        repo = RepoRepository(db)
        await repo.replace_snapshot(
            binding_id,
            repo=SnapshotRow(
                repo_id="pay/checkout",
                ref="main",
                payload={
                    "repoId": "pay/checkout",
                    "fullName": "pay/checkout",
                    "defaultBranch": "main",
                    "sha": "a" * 40,
                },
            ),
            branches=(
                SnapshotRow(
                    repo_id="pay/checkout",
                    ref="main",
                    payload={
                        "name": "main",
                        "isDefault": True,
                        "headSha": "a" * 40,
                        "committedAt": "2026-11-20T02:00:00Z",
                    },
                ),
            ),
            commits=(
                SnapshotRow(
                    repo_id="pay/checkout",
                    ref="main",
                    payload={
                        "sha": "a" * 40,
                        "shortSha": "a" * 7,
                        "title": "init",
                        "authorName": "lin.t",
                        "committedAt": "2026-11-20T02:00:00Z",
                    },
                ),
            ),
            fetched_at=fetched_at,
        )
        await db.commit()

    def forbidden_provider(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("baseline 不得调用供应商")

    monkeypatch.setattr(sync_service, "build_provider", forbidden_provider)

    document = await browse_service.read_baseline(binding_id)

    assert document["metadataSynced"] is True
    assert document["repo"]["repoId"] == "pay/checkout"
    assert document["branches"][0]["isDefault"] is True
    assert document["commits"][0]["shortSha"] == "a" * 7
    assert document["fetchedAt"].endswith("Z")
    assert document["revoked"] is False

    async with database.sessionmaker() as db:
        await RepoRepository(db).unbind(binding_id)
        await db.commit()

    revoked = await browse_service.read_baseline(binding_id)
    assert revoked["revoked"] is True
    assert revoked["metadataSynced"] is True
    assert revoked["commits"][0]["sha"] == "a" * 40


class _EndlessBranchProvider(_FakeProvider):
    async def list_branches(self, repo, *, search, cursor, limit):  # noqa: ANN001, ANN201
        return Page(items=(), next_cursor="2")


async def test_tc221_sync_aborts_after_branch_page_guard(
    database, monkeypatch
) -> None:
    async with database.sessionmaker() as db:
        project = await _project(db)
        binding = _token_binding(project.project_id)
        db.add(binding)
        binding_id = binding.binding_id
        await db.commit()

    monkeypatch.setattr(
        sync_service,
        "build_provider",
        _fake_factory(_EndlessBranchProvider()),
    )

    result = await sync_service.sync_binding(binding_id)

    assert result["record"]["status"] == "failed"
    assert result["record"]["errorCategory"] == "other"
    assert result["record"]["errorMessage"] == sync_service.BRANCH_LIMIT_MESSAGE
    async with database.sessionmaker() as db:
        rows = list(
            await db.scalars(
                select(RepoMetadataSnapshot).where(
                    RepoMetadataSnapshot.binding_id == binding_id
                )
            )
        )
    assert rows == []
