"""知识库删除生命周期与横切 API 契约。用例名带 TC 编号。"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_project,
    seed_session_graph,
)
from workbench.db.models import AiCallRecord, KnowledgeBase, KnowledgeEntry, SessionEvent
from workbench.services.ai_gateway import AiGateway
from workbench.services.knowledge import lifecycle_service as lifecycle_module
from workbench.services.knowledge.registration import (
    install_injection_preparer,
    uninstall_injection_preparer,
)

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"
BASES_URL = "/api/v1/knowledge-bases"
CANDIDATES_URL = "/api/v1/sessions/{session_id}/knowledge-injection/candidates"
PREVIEW_URL = "/api/v1/sessions/{session_id}/knowledge-injection/preview"
COMPLETE_URL = "/api/v1/sessions/{session_id}/ai/complete"


class FakeAdapter:
    async def complete(self, **kwargs):  # noqa: ANN003, ANN201
        return "模型回答"

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


def make_index(
    entries: list[dict[str, Any]], *, name: str, generated_at: str | None = None
) -> bytes:
    document: dict[str, Any] = {
        "schema": "knowledge/v1",
        "name": name,
        "entries": entries,
    }
    if generated_at is not None:
        document["generated_at"] = generated_at
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


def _files(index: bytes) -> list[tuple[str, tuple[str, bytes, str]]]:
    return [("files", ("index.json", index, "application/json"))]


@pytest_asyncio.fixture
async def api(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(
        settings=settings,
        database=database,
        ai_gateway=AiGateway(adapter=FakeAdapter(), retry_backoff=0),
    )
    install_injection_preparer(app)
    try:
        async with build_client(app) as client:
            login = await client.post(
                "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
            )
            assert login.status_code == 200
            yield client, database, settings
    finally:
        uninstall_injection_preparer()


async def _import(
    client,  # noqa: ANN001
    project_id: int,
    entries: list[dict[str, Any]],
    *,
    name: str,
    generated_at: str | None = None,
) -> dict[str, Any]:
    response = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": name},
        files=_files(make_index(entries, name=name, generated_at=generated_at)),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["kb"]


def _dir(settings, kb_id: str):  # noqa: ANN001, ANN202
    return settings.data_path / "knowledge-bases" / kb_id


async def _totals(sm) -> tuple[int, int]:  # noqa: ANN001
    async with sm() as db:
        bases = await db.scalar(select(func.count()).select_from(KnowledgeBase))
        entries = await db.scalar(select(func.count()).select_from(KnowledgeEntry))
    return int(bases or 0), int(entries or 0)


@pytest.mark.asyncio
async def test_tc139_delete_removes_all_versions_entries_and_files(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    first = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "旧版", "zh_definition": "旧定义"}],
        name="库",
    )
    second = await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "新版", "zh_definition": "新定义"},
            {"id": "TERM-001", "zh_name": "收单", "zh_definition": "受理支付"},
        ],
        name="库",
    )
    assert _dir(settings, first["kbId"]).is_dir()
    assert _dir(settings, second["kbId"]).is_dir()

    response = await client.delete(f"{BASES_URL}/{second['kbId']}", headers=ORIGIN)
    assert response.status_code == 204
    assert response.text == ""

    assert await _totals(database.sessionmaker) == (0, 0)
    assert not _dir(settings, first["kbId"]).exists()
    assert not _dir(settings, second["kbId"]).exists()
    trash = settings.data_path / ".trash"
    assert not trash.exists() or list(trash.iterdir()) == []

    listing = await client.get(BASES_URL, params={"projectId": project_id})
    assert listing.status_code == 200
    assert listing.json()["items"] == []
    detail = await client.get(f"{BASES_URL}/{second['kbId']}")
    assert detail.status_code == 404
    assert detail.json()["code"] == "kb_not_found"


@pytest.mark.asyncio
async def test_tc140_history_survives_delete_and_is_flagged(api) -> None:
    client, database, _settings = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        name="库",
    )

    called = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={
            "prompt": "请分析",
            "knowledgeRefs": [
                {"kbId": kb["kbId"], "entryCodes": ["ENT-001"]}
            ],
        },
        headers=ORIGIN,
    )
    assert called.status_code == 200, called.text
    call_id = called.json()["callId"]

    async with database.sessionmaker() as db:
        record = await db.get(AiCallRecord, call_id)
        assert record is not None
        before = {
            "knowledge_injection": record.knowledge_injection,
            "injected_chars": record.injected_chars,
            "prompt_chars": record.prompt_chars,
            "total_chars": record.total_chars,
        }
        events_before = await db.scalar(
            select(func.count())
            .select_from(SessionEvent)
            .where(SessionEvent.session_id == session_id)
        )

    deleted = await client.delete(f"{BASES_URL}/{kb['kbId']}", headers=ORIGIN)
    assert deleted.status_code == 204

    async with database.sessionmaker() as db:
        record = await db.get(AiCallRecord, call_id)
        assert record is not None
        assert record.knowledge_injection == before["knowledge_injection"]
        assert record.injected_chars == before["injected_chars"]
        assert record.prompt_chars == before["prompt_chars"]
        assert record.total_chars == before["total_chars"]
        events_after = await db.scalar(
            select(func.count())
            .select_from(SessionEvent)
            .where(SessionEvent.session_id == session_id)
        )
    assert events_after == events_before

    detail = await client.get(f"/api/v1/calls/{call_id}")
    assert detail.status_code == 200
    injected = detail.json()["knowledgeInjection"]
    assert [item["kbId"] for item in injected] == [kb["kbId"]]
    assert injected[0]["kbDeleted"] is True
    assert injected[0]["kbName"] == "库"
    assert injected[0]["entryCodes"] == ["ENT-001"]


@pytest.mark.asyncio
async def test_tc141_delete_is_scoped_to_one_logical_kb(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    other_project = await seed_project(database.sessionmaker, name="其他项目")
    target = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        name="库A",
    )
    sibling = await _import(
        client,
        project_id,
        [{"id": "ENT-002", "zh_name": "退款单", "zh_definition": "一次退款请求"}],
        name="库B",
    )
    elsewhere = await _import(
        client,
        other_project,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "另一个项目"}],
        name="库A",
    )

    response = await client.delete(f"{BASES_URL}/{target['kbId']}", headers=ORIGIN)
    assert response.status_code == 204

    async with database.sessionmaker() as db:
        remaining_ids = set(await db.scalars(select(KnowledgeBase.kb_id)))
        remaining_codes = set(await db.scalars(select(KnowledgeEntry.code)))
    assert remaining_ids == {sibling["kbId"], elsewhere["kbId"]}
    assert remaining_codes == {"ENT-002", "ENT-001"}

    listing = await client.get(BASES_URL, params={"projectId": project_id})
    assert [item["kbId"] for item in listing.json()["items"]] == [sibling["kbId"]]
    other_listing = await client.get(
        BASES_URL, params={"projectId": other_project}
    )
    assert [item["kbId"] for item in other_listing.json()["items"]] == [
        elsewhere["kbId"]
    ]


@pytest.mark.asyncio
async def test_tc142_file_cleanup_failure_still_returns_204(api, monkeypatch) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        name="库",
    )

    logged: list[str] = []
    monkeypatch.setattr(
        lifecycle_module.logger,
        "warning",
        lambda message, *args, **_kwargs: logged.append(message % args),
    )

    def boom(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
        raise OSError("simulated cleanup failure")

    monkeypatch.setattr(shutil, "rmtree", boom)

    response = await client.delete(f"{BASES_URL}/{kb['kbId']}", headers=ORIGIN)
    assert response.status_code == 204
    assert await _totals(database.sessionmaker) == (0, 0)
    assert not _dir(settings, kb["kbId"]).exists()
    trash_entries = list((settings.data_path / ".trash").iterdir())
    assert len(trash_entries) == 1
    assert trash_entries[0].name.startswith(kb["kbId"])

    assert logged == ["knowledge-base trash cleanup failed count=1"]


@pytest.mark.asyncio
async def test_tc147_all_endpoints_require_session(api) -> None:
    client, _database, _settings = api
    client.cookies.clear()
    kb_id = "0" * 32
    entry_id = "1" * 32
    endpoints = [
        ("POST", IMPORT_URL, None),
        ("GET", BASES_URL, None),
        ("GET", f"{BASES_URL}/{kb_id}", None),
        ("GET", f"{BASES_URL}/{kb_id}/versions", None),
        ("DELETE", f"{BASES_URL}/{kb_id}", None),
        ("GET", "/api/v1/knowledge-entries", None),
        ("GET", f"{BASES_URL}/{kb_id}/entries", None),
        ("GET", f"/api/v1/knowledge-entries/{entry_id}", None),
        ("GET", CANDIDATES_URL.format(session_id=1), None),
        (
            "POST",
            PREVIEW_URL.format(session_id=1),
            {"refs": [], "userPrompt": "x"},
        ),
    ]
    for method, url, payload in endpoints:
        response = await client.request(
            method, url, json=payload, headers=ORIGIN
        )
        assert response.status_code == 401, (method, url, response.text)
        body = response.json()
        assert body["code"] == "unauthorized"
        assert body["details"] == []


@pytest.mark.asyncio
async def test_tc148_error_body_and_time_format(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)

    missing = await client.delete(f"{BASES_URL}/{'0' * 32}", headers=ORIGIN)
    assert missing.status_code == 404
    body = missing.json()
    assert set(body) == {"code", "message", "details", "requestId"}
    assert body["code"] == "kb_not_found"
    assert isinstance(body["details"], list)
    assert body["requestId"] == missing.headers["X-Request-Id"]
    assert body["requestId"]

    invalid = await client.post(
        PREVIEW_URL.format(session_id=1), json={}, headers=ORIGIN
    )
    assert invalid.status_code == 400
    invalid_body = invalid.json()
    assert invalid_body["code"] == "validation_error"
    assert isinstance(invalid_body["details"], list)
    assert invalid_body["details"]
    assert all({"field", "message"} <= set(item) for item in invalid_body["details"])

    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        name="库",
        generated_at="2026-09-28T00:00:00Z",
    )
    listing = await client.get(BASES_URL, params={"projectId": project_id})
    item = listing.json()["items"][0]
    for field in ("createdAt", "generatedAt"):
        value = item[field]
        assert value is not None and value.endswith("Z")
        datetime.fromisoformat(value[:-1])

    detail = await client.get(f"{BASES_URL}/{kb['kbId']}")
    assert detail.status_code == 200
    assert detail.json()["kb"]["createdAt"].endswith("Z")
