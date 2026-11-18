"""文件存储路径隔离与清理。用例名带 TC 编号。"""

from __future__ import annotations

import io
import os
from datetime import timedelta

import pytest
from sqlalchemy import func, select

from helpers import seed_model, seed_project, seed_provider, seed_session
from workbench.adapters.fs.storage import (
    ArtifactNotFound,
    artifact_dir,
    move_to_trash,
    safe_artifact_path,
    scan_orphans,
    tmp_dir,
)
from workbench.db.models import Artifact
from workbench.services import artifacts
from workbench.services.errors import DomainError


def _prepare(settings, session_id: int = 1):
    directory = artifact_dir(session_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def test_tc039_path_traversal_rejected(settings) -> None:
    directory = _prepare(settings, 1)
    file_path = directory / "ok.log"
    file_path.write_text("ok", encoding="utf-8")
    assert safe_artifact_path(1, f"sessions/1/{file_path.name}") == file_path.resolve()

    for bad in (
        "../../etc/passwd",
        "..%2Fetc%2Fpasswd",
        f"sessions/1/../2/other.log",
        "/etc/passwd",
    ):
        with pytest.raises(ArtifactNotFound):
            safe_artifact_path(1, bad)

    outside = settings.data_path / "outside.log"
    outside.parent.mkdir(parents=True, exist_ok=True)
    outside.write_text("outside", encoding="utf-8")
    link = directory / "link.log"
    os.symlink(outside, link)
    with pytest.raises(ArtifactNotFound):
        safe_artifact_path(1, f"sessions/1/{link.name}")


def test_tc040_storage_cleanup_and_trash(settings) -> None:
    directory = _prepare(settings, 2)
    (directory / "a.log").write_text("a", encoding="utf-8")
    trashed = move_to_trash(2)
    assert trashed is not None and trashed.exists()
    assert not directory.exists()

    tmp_dir().mkdir(parents=True, exist_ok=True)
    stale = tmp_dir() / "stale.part"
    stale.write_text("x", encoding="utf-8")
    old = os.stat(stale).st_mtime - timedelta(hours=25).total_seconds()
    os.utime(stale, (old, old))
    removed = scan_orphans(timedelta(hours=24))
    assert removed >= 1
    assert not stale.exists()


@pytest.mark.asyncio
async def test_tc040_storage_cleanup_on_failure(database, settings, monkeypatch) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    def broken_replace(*args, **kwargs):  # noqa: ANN002, ANN003
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("workbench.adapters.fs.storage.os.replace", broken_replace)
    with pytest.raises(DomainError) as err:
        await artifacts.save(
            session_id, file_name="app.log", source=io.BytesIO(b"payload")
        )
    assert err.value.code == "artifact_write_failed"

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(Artifact)) == 0
    if artifact_dir(session_id).exists():
        assert list(artifact_dir(session_id).iterdir()) == []
    assert list(tmp_dir().iterdir()) == []
