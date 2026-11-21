"""知识库导入服务与文件存储。用例名带 TC 编号。"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from helpers import make_app, seed_project
from workbench.adapters.fs.knowledge_storage import KbStorage
from workbench.db.models import KnowledgeBase, KnowledgeEntry
from workbench.db.repositories import knowledge as knowledge_repo
from workbench.services.errors import DomainError
from workbench.services.knowledge import KnowledgeImportService, scan_orphan_dirs


class Upload:
    """最小 UploadFile 替身：支持 ``await read(size)``。"""

    def __init__(self, name: str, data: bytes) -> None:
        self.filename = name
        self._data = data
        self._pos = 0

    async def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            chunk = self._data[self._pos :]
        else:
            chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


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


def _uploads(entries: list[dict[str, Any]] | None = None) -> list[Upload]:
    return [
        Upload("index.json", make_index(entries or ENTRIES)),
        Upload("ENT-001.md", "# 支付单\n\n正文内容".encode("utf-8")),
    ]


def _root(settings) -> Path:  # noqa: ANN001
    return settings.data_path / "knowledge-bases"


async def _assert_clean(sm, settings) -> None:  # noqa: ANN001
    async with sm() as db:
        assert await db.scalar(select(func.count()).select_from(KnowledgeBase)) == 0
        assert await db.scalar(select(func.count()).select_from(KnowledgeEntry)) == 0
    root = _root(settings)
    if root.exists():
        assert [p.name for p in root.iterdir() if p.name != ".staging"] == []
        staging = root / ".staging"
        if staging.exists():
            assert list(staging.iterdir()) == []


def test_tc116_client_filename_never_used_as_path(settings) -> None:
    storage = KbStorage()
    token = storage.new_token()
    payloads = [
        ("../../etc/passwd", b"evil"),
        ("a/b.md", b"markdown"),
        ("\x00bad\x01.md", b"control"),
    ]
    stored = storage.stage(token, payloads)

    root = storage.root.resolve()
    assert [item.storage_name.split("__", 1)[1] for item in stored] == [
        "passwd",
        "b.md",
        "bad.md",
    ]
    for item, (_name, data) in zip(stored, payloads, strict=True):
        assert item.storage_name.startswith(hashlib.sha256(data).hexdigest()[:16] + "__")
        path = (root / item.relative_path).resolve()
        assert path.is_relative_to(root)
        assert ".." not in Path(item.storage_name).parts
        assert path.read_bytes() == data

    for escaped in ("../escape", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError):
            storage.resolve_within(escaped)
    with pytest.raises(ValueError):
        storage.target_dir("../../etc")


@pytest.mark.asyncio
async def test_tc113_rolls_back_all_on_failure(settings, database, monkeypatch) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    service = KnowledgeImportService(sessionmaker=sm)

    def fail_parse(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("parse boom")

    with monkeypatch.context() as patch:
        patch.setattr(
            "workbench.services.knowledge.import_service.parse_index", fail_parse
        )
        with pytest.raises(RuntimeError):
            await service.import_files(project_id=project_id, name=None, files=_uploads())
        await _assert_clean(sm, settings)

    async def fail_write(self, db, rows) -> None:  # noqa: ANN001
        raise RuntimeError("write boom")

    with monkeypatch.context() as patch:
        patch.setattr(KnowledgeImportService, "_write_rows", fail_write)
        with pytest.raises(RuntimeError):
            await service.import_files(project_id=project_id, name=None, files=_uploads())
        await _assert_clean(sm, settings)

    async def fail_bulk(db, rows) -> None:  # noqa: ANN001
        raise RuntimeError("bulk boom")

    with monkeypatch.context() as patch:
        patch.setattr(knowledge_repo, "bulk_insert_entries", fail_bulk)
        with pytest.raises(RuntimeError):
            await service.import_files(project_id=project_id, name=None, files=_uploads())
        await _assert_clean(sm, settings)


@pytest.mark.asyncio
async def test_tc115_concurrent_import_conflict_returns_409(
    settings, database, monkeypatch
) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    service = KnowledgeImportService(sessionmaker=sm)
    attempts = {"count": 0}

    async def collide(db, rows) -> None:  # noqa: ANN001
        attempts["count"] += 1
        raise IntegrityError(
            "INSERT INTO knowledge_base",
            {},
            Exception("UNIQUE constraint failed: knowledge_base.project_id"),
        )

    with monkeypatch.context() as patch:
        patch.setattr(knowledge_repo, "bulk_insert_entries", collide)
        with pytest.raises(DomainError) as error:
            await service.import_files(project_id=project_id, name=None, files=_uploads())

    assert error.value.code == "kb_name_conflict"
    assert error.value.status_code == 409
    assert attempts["count"] == 2
    await _assert_clean(sm, settings)


@pytest.mark.asyncio
async def test_tc117_startup_scan_removes_orphan_dirs(settings, database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    live_id = "1" * 32
    old_orphan = "a" * 32
    fresh_orphan = "b" * 32

    async with sm() as db:
        db.add(
            KnowledgeBase(
                kb_id=live_id,
                project_id=project_id,
                name="在用知识库",
                name_key="在用知识库",
                version=1,
                current_flag="1",
                status="ready",
                entry_count=0,
                file_count=0,
                total_byte_size=0,
                source_index_sha256="0" * 64,
                storage_dir=f"knowledge-bases/{live_id}",
            )
        )
        await db.commit()

    storage = KbStorage()
    storage.root.mkdir(parents=True, exist_ok=True)
    live_dir = storage.target_dir(live_id)
    live_dir.mkdir()
    old_dir = storage.root / old_orphan
    old_dir.mkdir()
    fresh_dir = storage.root / fresh_orphan
    fresh_dir.mkdir()
    stale = os.stat(old_dir).st_mtime - timedelta(hours=2).total_seconds()
    os.utime(old_dir, (stale, stale))

    removed = await scan_orphan_dirs(
        sessionmaker=sm, storage=storage, max_age=timedelta(hours=1)
    )

    assert removed == 1
    assert old_dir.exists() is False
    assert live_dir.exists()
    assert fresh_dir.exists()

    # 启动生命周期接线：lifespan 也会扫描并清理旧孤儿目录。
    wired_orphan = storage.root / ("c" * 32)
    wired_orphan.mkdir()
    os.utime(wired_orphan, (stale, stale))
    app = make_app(settings=settings, database=database)
    async with app.router.lifespan_context(app):
        pass
    assert wired_orphan.exists() is False
