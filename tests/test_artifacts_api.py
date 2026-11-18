"""制品上传、元数据、预览与下载接口。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_session_graph
from workbench.adapters.fs import storage
from workbench.db.models import Artifact, SessionEvent

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


@pytest.fixture
async def ctx(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as client:
        await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        project_id, model_id, session_id = await seed_session_graph(database.sessionmaker)
        yield client, database, session_id


async def _upload(client, session_id: int, files):  # noqa: ANN001
    return await client.post(
        f"/api/v1/sessions/{session_id}/artifacts", files=files, headers=ORIGIN
    )


@pytest.mark.asyncio
async def test_tc036_upload_success_and_preview(ctx) -> None:
    client, database, session_id = ctx
    response = await _upload(
        client, session_id, [("files", ("app.log", b"hello log\n", "text/plain"))]
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"items", "events"}
    item = body["items"][0]
    assert item["fileName"] == "app.log"
    assert item["mimeType"].startswith("text/plain")
    assert item["byteSize"] == 10
    assert "relativePath" not in item and "storageName" not in item
    assert body["events"][0]["type"] == "artifact"

    meta = await client.get(f"/api/v1/artifacts/{item['artifactId']}")
    assert meta.status_code == 200
    assert meta.json()["fileName"] == "app.log"

    content = await client.get(f"/api/v1/artifacts/{item['artifactId']}/content")
    assert content.status_code == 200
    assert content.content == b"hello log\n"
    assert content.headers["content-type"].startswith("text/plain")
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.headers["content-disposition"].startswith("inline")
    assert "app.log" in content.headers["content-disposition"]

    download = await client.get(
        f"/api/v1/artifacts/{item['artifactId']}/content?mode=download"
    )
    assert download.headers["content-disposition"].startswith("attachment")

    oversized = await client.get(
        f"/api/v1/artifacts/{item['artifactId']}/content?max_bytes=262145"
    )
    assert oversized.status_code == 400

    events = await client.get(f"/api/v1/sessions/{session_id}/events")
    assert [event["type"] for event in events.json()["items"]] == ["artifact"]


@pytest.mark.asyncio
async def test_tc037_batch_validation_rejects_all(ctx) -> None:
    client, database, session_id = ctx

    mixed = await _upload(
        client,
        session_id,
        [
            ("files", ("ok.txt", b"fine", "text/plain")),
            ("files", ("bad.exe", b"MZ", "application/octet-stream")),
        ],
    )
    assert mixed.status_code == 400
    assert mixed.json()["code"] == "file_type_not_allowed"

    too_large = await _upload(
        client,
        session_id,
        [("files", ("big.log", b"x" * (10 * 1024 * 1024 + 1), "text/plain"))],
    )
    assert too_large.status_code == 400
    assert too_large.json()["code"] == "file_too_large"

    too_many = await _upload(
        client,
        session_id,
        [("files", (f"f{i}.txt", b"x", "text/plain")) for i in range(11)],
    )
    assert too_many.status_code == 400
    assert too_many.json()["code"] == "too_many_files"

    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(Artifact)) == 0
        assert (
            await db.scalar(select(func.count()).select_from(SessionEvent)) == 0
        )
    assert not storage.artifact_dir(session_id).exists() or not any(
        storage.artifact_dir(session_id).iterdir()
    )


@pytest.mark.asyncio
async def test_tc038_duplicate_names_renamed(ctx) -> None:
    client, database, session_id = ctx
    await _upload(client, session_id, [("files", ("app.log", b"one", "text/plain"))])
    await _upload(client, session_id, [("files", ("app.log", b"two", "text/plain"))])
    await _upload(client, session_id, [("files", ("app.log", b"three", "text/plain"))])

    async with database.sessionmaker() as db:
        rows = list(
            await db.scalars(select(Artifact).order_by(Artifact.artifact_id.asc()))
        )
    assert [row.file_name for row in rows] == ["app.log", "app-1.log", "app-2.log"]

    contents = []
    for row in rows:
        response = await client.get(f"/api/v1/artifacts/{row.artifact_id}/content")
        contents.append(response.content)
    assert contents == [b"one", b"two", b"three"]


@pytest.mark.asyncio
async def test_tc039_traversal_rejected_via_api(ctx) -> None:
    client, database, session_id = ctx
    response = await _upload(
        client,
        session_id,
        [("files", ("../../escape.txt", b"payload", "text/plain"))],
    )
    assert response.status_code == 201
    item = response.json()["items"][0]
    assert item["fileName"] == "escape.txt"

    from workbench.db.models import Artifact as ArtifactRow

    async with database.sessionmaker() as db:
        row = await db.get(ArtifactRow, item["artifactId"])
        assert row.storage_name.endswith(".txt")
        assert ".." not in row.storage_name
        assert row.relative_path == f"sessions/{session_id}/{row.storage_name}"
    assert not (storage.data_dir() / "escape.txt").exists()
    assert not (storage.data_dir().parent / "escape.txt").exists()

    # 路径穿越式读取必须落到 404，而不是读到会话目录外文件。
    missing = await client.get("/api/v1/artifacts/999999/content")
    assert missing.status_code == 404
    assert missing.json()["code"] == "artifact_not_found"


@pytest.mark.asyncio
async def test_tc040_disk_failure_returns_507(ctx, monkeypatch) -> None:
    client, database, session_id = ctx
    before = (
        (await client.get(f"/api/v1/sessions/{session_id}")).json()["updatedAt"]
    )

    def boom(source, path):  # noqa: ANN001
        raise OSError(28, "No space left on device")

    monkeypatch.setattr("workbench.services.artifacts._write_limited", boom)
    response = await _upload(
        client, session_id, [("files", ("app.log", b"data", "text/plain"))]
    )
    assert response.status_code == 507
    assert response.json()["code"] == "artifact_write_failed"

    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(Artifact)) == 0
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == 0

    after = (await client.get(f"/api/v1/sessions/{session_id}")).json()["updatedAt"]
    assert after == before
    assert not storage.tmp_dir().exists() or not any(storage.tmp_dir().iterdir())
