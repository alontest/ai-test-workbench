"""知识库导入 API。用例名带 TC 编号。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.models import KnowledgeBase, KnowledgeEntry
from workbench.db.repositories import knowledge as knowledge_repo
from workbench.knowledge.config import get_kb_settings

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"


def make_index(
    entries: list[dict[str, Any]],
    *,
    name: str = "支付域知识库",
    generated_at: str | None = None,
) -> bytes:
    document: dict[str, Any] = {"schema": "knowledge/v1", "name": name, "entries": entries}
    if generated_at is not None:
        document["generated_at"] = generated_at
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


ENTRIES = [
    {"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"},
    {"id": "TERM-001", "zh_name": "收单", "zh_definition": "受理支付"},
]


def _files(
    index: bytes, docs: dict[str, bytes] | None = None
) -> list[tuple[str, tuple[str, bytes, str]]]:
    items = [("files", ("index.json", index, "application/json"))]
    for file_name, data in (docs or {}).items():
        items.append(("files", (file_name, data, "text/markdown")))
    return items


@pytest_asyncio.fixture
async def api(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings=settings, database=database)
    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        yield client, database, settings


@pytest.fixture
def kb_env(monkeypatch):
    def apply(**values: int) -> None:
        for key, value in values.items():
            monkeypatch.setenv(key, str(value))
        get_kb_settings.cache_clear()

    yield apply
    get_kb_settings.cache_clear()


def _root(settings) -> Path:  # noqa: ANN001
    return settings.data_path / "knowledge-bases"


async def _assert_no_rows(sm) -> None:  # noqa: ANN001
    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(KnowledgeBase)) == 0
        assert await db.scalar(select(func.count()).select_from(KnowledgeEntry)) == 0


def _assert_no_kb_dirs(settings) -> None:  # noqa: ANN001
    root = _root(settings)
    if root.exists():
        assert [p.name for p in root.iterdir() if p.name != ".staging"] == []
        staging = root / ".staging"
        if staging.exists():
            assert list(staging.iterdir()) == []


@pytest.mark.asyncio
async def test_tc111_imports_knowledge_base_and_lists_it(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)

    response = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id)},
        files=_files(
            make_index(ENTRIES, generated_at="2026-09-28T00:00:00Z"),
            {"ENT-001.md": "# 支付单\n\n正文内容".encode("utf-8")},
        ),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    kb = body["kb"]
    report = body["importReport"]

    assert len(kb["kbId"]) == 32
    assert kb["projectId"] == project_id
    assert kb["name"] == "支付域知识库"
    assert kb["version"] == 1
    assert kb["current"] is True
    assert kb["status"] == "ready"
    assert kb["generatedAt"] == "2026-09-28T00:00:00Z"
    assert kb["entryCount"] == 2
    assert kb["fileCount"] == 2
    assert kb["supersededCount"] == 0
    assert kb["latestKbId"] == kb["kbId"]
    assert kb["createdAt"].endswith("Z")
    assert report["counts"]["files"] == 2
    assert report["counts"]["bytes"] > 0
    assert report["counts"]["entries"] == 2
    assert report["counts"]["skipped"] == 0
    assert report["skippedEntries"] == []
    assert report["versionBumped"] is False
    assert report["previousVersion"] is None

    sm = database.sessionmaker
    async with sm() as db:
        rows = list(await knowledge_repo.list_bases(db, limit=10))
        assert [row.kb_id for row in rows] == [kb["kbId"]]
        entry = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb["kbId"], KnowledgeEntry.code == "ENT-001"
            )
        )
        assert entry is not None
        assert entry.body == "# 支付单\n\n正文内容"
        assert entry.body_missing is False

    stored = _root(settings) / kb["kbId"]
    assert (stored / "index.json").is_file()
    manifest = json.loads((stored / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["kbId"] == kb["kbId"]
    assert manifest["version"] == 1
    assert len(manifest["files"]) == 2


@pytest.mark.asyncio
async def test_tc112_rejects_upload_limit_violations_per_file(
    api, kb_env
) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    index = make_index(ENTRIES)

    async def post(files):  # noqa: ANN001, ANN202
        return await client.post(
            IMPORT_URL,
            data={"projectId": str(project_id)},
            files=files,
            headers=ORIGIN,
        )

    unsupported = await post(
        _files(index, {"notes.txt": b"plain"})
    )
    assert unsupported.status_code == 400
    assert unsupported.json()["code"] == "unsupported_file_type"
    assert unsupported.json()["details"][0]["fileName"] == "notes.txt"
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)

    kb_env(AW_KB_MAX_FILE_BYTES=10)
    too_large = await post(_files(index, {"notes.md": b"x" * 11}))
    assert too_large.status_code == 400
    assert too_large.json()["code"] == "file_too_large"
    assert too_large.json()["details"][0]["actual"] == 11
    assert too_large.json()["details"][0]["limit"] == 10
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)

    kb_env(AW_KB_MAX_FILE_BYTES=1024, AW_KB_MAX_FILES=2)
    too_many = await post(_files(index, {"a.md": b"a", "b.md": b"b"}))
    assert too_many.status_code == 400
    assert too_many.json()["code"] == "too_many_files"
    assert too_many.json()["details"][0]["limit"] == 2
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)

    kb_env(
        AW_KB_MAX_FILE_BYTES=100_000,
        AW_KB_MAX_TOTAL_BYTES=4096,
        AW_KB_MAX_FILES=50,
    )
    too_big = await post(_files(index, {"a.md": b"a" * 3000, "b.md": b"b" * 3000}))
    assert too_big.status_code == 413
    assert too_big.json()["code"] == "kb_import_too_large"
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)

    kb_env(
        AW_KB_MAX_FILE_BYTES=100_000,
        AW_KB_MAX_TOTAL_BYTES=1_000_000,
        AW_KB_MAX_FILES=50,
    )
    missing = await post([("files", ("notes.md", b"body", "text/markdown"))])
    assert missing.status_code == 400
    assert missing.json()["code"] == "index_json_missing"
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)


@pytest.mark.asyncio
async def test_tc104_fails_when_no_entry_importable(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    sentinel = "SENTINEL-BODY-SHOULD-NOT-LEAK"
    index = make_index([{"zh_name": "无编号", "zh_definition": sentinel}])

    response = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id)},
        files=_files(index),
        headers=ORIGIN,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "index_json_invalid"
    assert sentinel not in json.dumps(body, ensure_ascii=False)
    await _assert_no_rows(database.sessionmaker)
    _assert_no_kb_dirs(settings)


@pytest.mark.asyncio
async def test_tc114_reimport_creates_new_version_and_supersedes_old(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)

    first = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": "支付域知识库"},
        files=_files(make_index(ENTRIES)),
        headers=ORIGIN,
    )
    assert first.status_code == 201, first.text
    assert first.json()["kb"]["version"] == 1

    second = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": "支付域知识库"},
        files=_files(make_index([ENTRIES[0]])),
        headers=ORIGIN,
    )
    assert second.status_code == 201, second.text
    new_kb = second.json()["kb"]
    assert new_kb["version"] == 2
    assert second.json()["importReport"]["versionBumped"] is True
    assert second.json()["importReport"]["previousVersion"] == 1
    assert new_kb["supersededCount"] == 1

    sm = database.sessionmaker
    async with sm() as db:
        rows = list(
            (
                await db.scalars(
                    select(KnowledgeBase).order_by(KnowledgeBase.version.asc())
                )
            ).all()
        )
        assert len(rows) == 2
        old, new = rows
        assert old.status == "superseded"
        assert old.current_flag is None
        assert old.superseded_by_kb_id == new.kb_id
        assert new.status == "ready"
        assert new.current_flag == "1"
        current_count = await db.scalar(
            select(func.count())
            .select_from(KnowledgeBase)
            .where(KnowledgeBase.current_flag == "1")
        )
        assert current_count == 1

    assert (_root(settings) / old.kb_id).is_dir()
    assert (_root(settings) / new.kb_id).is_dir()


@pytest.mark.asyncio
async def test_tc145_large_body_roundtrip_not_truncated(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    payload = "A" * (70 * 1024)
    entries = [{"id": "ENT-BIG", "zh_name": "大正文", "zh_definition": "摘要"}]

    response = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id)},
        files=_files(make_index(entries), {"ENT-BIG.md": payload.encode("utf-8")}),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    kb_id = response.json()["kb"]["kbId"]

    async with database.sessionmaker() as db:
        entry = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb_id, KnowledgeEntry.code == "ENT-BIG"
            )
        )
    assert entry is not None
    assert entry.body_missing is False
    assert entry.body == payload
    assert len(entry.body.encode("utf-8")) == len(payload.encode("utf-8"))
