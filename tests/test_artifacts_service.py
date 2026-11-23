"""制品落盘冻结签名。用例名带 TC 编号。"""

from __future__ import annotations

import inspect
import io

import pytest
from sqlalchemy import func, select

from helpers import seed_model, seed_project, seed_provider, seed_session
from vigil_workbench.adapters.fs.storage import artifact_dir
from vigil_workbench.db.models import Artifact, SessionEvent
from vigil_workbench.services import artifacts
from vigil_workbench.services.errors import DomainError


def test_tc057_frozen_artifact_signature() -> None:
    sig = inspect.signature(artifacts.save)
    assert list(sig.parameters) == [
        "session_id",
        "file_name",
        "source",
        "claimed_content_type",
        "kind",
    ]
    assert sig.parameters["file_name"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["claimed_content_type"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["claimed_content_type"].default is None
    assert sig.parameters["kind"].kind is inspect.Parameter.KEYWORD_ONLY
    assert sig.parameters["kind"].default == "upload"


@pytest.mark.asyncio
async def test_tc036_save_upload_success(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    view = await artifacts.save(
        session_id,
        file_name="app.log",
        source=io.BytesIO(b"hello\n"),
        claimed_content_type="application/octet-stream",
    )
    assert set(view) == {
        "artifact_id",
        "session_id",
        "kind",
        "file_name",
        "mime_type",
        "byte_size",
        "created_at",
    }
    assert view["file_name"] == "app.log"
    assert view["mime_type"] == "text/plain"
    assert view["byte_size"] == 6
    assert view["kind"] == "upload"
    assert "relative_path" not in view and "storage_name" not in view

    async with sm() as db:
        row = await db.get(Artifact, view["artifact_id"])
        assert row is not None
        disk_path = artifact_dir(session_id) / row.storage_name
        assert disk_path.read_bytes() == b"hello\n"
        assert row.relative_path == f"sessions/{session_id}/{row.storage_name}"
        events = (
            await db.scalars(
                select(SessionEvent).where(SessionEvent.session_id == session_id)
            )
        ).all()
        assert [e.type for e in events] == ["artifact"]
        assert events[0].payload["fileName"] == "app.log"


@pytest.mark.asyncio
async def test_tc038_duplicate_name_renamed(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    first = await artifacts.save(session_id, file_name="app.log", source=io.BytesIO(b"one"))
    second = await artifacts.save(session_id, file_name="app.log", source=io.BytesIO(b"two"))
    assert first["file_name"] == "app.log"
    assert second["file_name"] == "app-1.log"

    async with sm() as db:
        rows = (await db.scalars(select(Artifact))).all()
        assert len(rows) == 2
        assert len({row.storage_name for row in rows}) == 2
    assert len(list(artifact_dir(session_id).iterdir())) == 2


@pytest.mark.asyncio
async def test_tc036_upload_rejections(database, settings) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)

    with pytest.raises(DomainError) as err:
        await artifacts.save(session_id, file_name="evil.exe", source=io.BytesIO(b"x"))
    assert err.value.code == "file_type_not_allowed"

    with pytest.raises(DomainError) as err:
        await artifacts.save(session_id, file_name="big.log", source=io.BytesIO(b"x" * (10 * 1024 * 1024 + 1)))
    assert err.value.code == "file_too_large"

    closed_id = await seed_session(
        sm, project_id=project_id, model_id=model_id, status="completed"
    )
    with pytest.raises(DomainError) as err:
        await artifacts.save(closed_id, file_name="app.log", source=io.BytesIO(b"x"))
    assert err.value.code == "session_closed"

    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(Artifact)) == 0
