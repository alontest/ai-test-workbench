"""知识库浏览/检索 API 与服务。用例名带 TC 编号。"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import event, update

from helpers import build_client, make_app, seed_admin, seed_project
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.models import KnowledgeBase, KnowledgeEntry
from vigil_workbench.knowledge.types import summary_digest
from vigil_workbench.services.knowledge.query_service import KnowledgeQueryService

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"
BASES_URL = "/api/v1/knowledge-bases"
ENTRIES_URL = "/api/v1/knowledge-entries"


def make_index(
    entries: list[dict[str, Any]],
    *,
    name: str = "支付域知识库",
    generated_at: str | None = None,
) -> bytes:
    document: dict[str, Any] = {
        "schema": "knowledge/v1",
        "name": name,
        "entries": entries,
    }
    if generated_at is not None:
        document["generated_at"] = generated_at
    return json.dumps(document, ensure_ascii=False).encode("utf-8")


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


async def _import(
    client,  # noqa: ANN001
    project_id: int,
    entries: list[dict[str, Any]],
    *,
    name: str | None = None,
    docs: dict[str, bytes] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    data = {"projectId": str(project_id)}
    if name is not None:
        data["name"] = name
    response = await client.post(
        IMPORT_URL,
        data=data,
        files=_files(make_index(entries, generated_at=generated_at), docs),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["kb"]


async def _entry_ids(client, params: dict[str, Any]) -> dict[str, str]:  # noqa: ANN001
    response = await client.get(ENTRIES_URL, params=params)
    assert response.status_code == 200, response.text
    return {item["code"]: item["entryId"] for item in response.json()["items"]}


@pytest.mark.asyncio
async def test_tc118_lists_entries_by_project_kb_and_type(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    other_project = await seed_project(database.sessionmaker, name="其他项目")
    kb_a = await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"},
            {"id": "TERM-001", "zh_name": "收单", "zh_definition": "受理支付"},
        ],
        name="库A",
    )
    kb_b = await _import(
        client,
        project_id,
        [{"id": "ST-001", "zh_name": "已支付", "zh_definition": "支付完成"}],
        name="库B",
    )
    await _import(
        client,
        other_project,
        [{"id": "ENT-900", "zh_name": "其他项目实体", "zh_definition": "不应出现"}],
        name="库C",
    )

    by_project = await client.get(ENTRIES_URL, params={"projectId": project_id})
    assert by_project.status_code == 200, by_project.text
    body = by_project.json()
    assert len(body["items"]) == 3
    assert body["total"] == 3
    assert {item["kbId"] for item in body["items"]} == {
        kb_a["kbId"],
        kb_b["kbId"],
    }

    by_kb = (
        await client.get(ENTRIES_URL, params={"kbId": kb_a["kbId"]})
    ).json()
    assert {item["code"] for item in by_kb["items"]} == {"ENT-001", "TERM-001"}

    by_type = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "type": "entity"})
    ).json()
    assert [item["code"] for item in by_type["items"]] == ["ENT-001"]
    assert by_type["total"] == 1

    by_kb_type = (
        await client.get(
            ENTRIES_URL, params={"kbId": kb_a["kbId"], "type": "term"}
        )
    ).json()
    assert [item["code"] for item in by_kb_type["items"]] == ["TERM-001"]

    empty = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "不存在"})
    ).json()
    assert empty["items"] == []
    assert empty["total"] == 0
    assert all(count == 0 for count in empty["countsByType"].values())


@pytest.mark.asyncio
async def test_tc119_searches_by_code_prefix_exact_and_keyword(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "Alpha", "zh_definition": "精确命中"},
            {"id": "ENT-0010", "zh_name": "Beta", "zh_definition": "前缀命中"},
            {"id": "TERM-002", "zh_name": "ENT-001 keyword", "zh_definition": "标题命中"},
            {"id": "ENT-101", "zh_name": "100% 完成", "zh_definition": "百分号"},
            {"id": "ENT-102", "zh_name": "a_b 字段", "zh_definition": "下划线"},
            {"id": "ENT-103", "zh_name": "C:\\tmp\\x", "zh_definition": "反斜杠"},
            {"id": "ENT-104", "zh_name": "axb 字段", "zh_definition": "不应命中下划线查询"},
        ],
        name="检索库",
        docs={"ENT-001.md": "分布式事务与补偿".encode("utf-8")},
    )

    ranked = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "ENT-001"})
    ).json()
    assert [item["code"] for item in ranked["items"]][:3] == [
        "ENT-001",
        "ENT-0010",
        "TERM-002",
    ]

    keyword = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "补偿"})
    ).json()
    assert [item["code"] for item in keyword["items"]] == ["ENT-001"]

    percent = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "100%"})
    ).json()
    assert [item["code"] for item in percent["items"]] == ["ENT-101"]

    underscore = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "a_b"})
    ).json()
    assert [item["code"] for item in underscore["items"]] == ["ENT-102"]

    backslash = (
        await client.get(ENTRIES_URL, params={"projectId": project_id, "q": "\\"})
    ).json()
    assert [item["code"] for item in backslash["items"]] == ["ENT-103"]

    too_long = await client.get(
        ENTRIES_URL, params={"projectId": project_id, "q": "x" * 101}
    )
    assert too_long.status_code == 400
    assert too_long.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_tc120_paginates_with_stable_cursor_and_counts_by_type(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    await _import(
        client,
        project_id,
        [
            {"id": f"ENT-00{index}", "zh_name": f"实体{index}", "zh_definition": "x"}
            for index in range(1, 6)
        ]
        + [
            {"id": "TERM-001", "zh_name": "术语一", "zh_definition": "x"},
            {"id": "TERM-002", "zh_name": "术语二", "zh_definition": "x"},
        ],
        name="分页库",
    )

    seen: list[str] = []
    cursor = None
    while True:
        params: dict[str, Any] = {"projectId": project_id, "limit": 2}
        if cursor is not None:
            params["cursor"] = cursor
        response = await client.get(ENTRIES_URL, params=params)
        assert response.status_code == 200, response.text
        body = response.json()
        seen.extend(item["code"] for item in body["items"])
        cursor = body["nextCursor"]
        if cursor is None:
            break
    assert len(seen) == 7
    assert len(set(seen)) == 7

    unfiltered = (
        await client.get(ENTRIES_URL, params={"projectId": project_id})
    ).json()
    entity_only = (
        await client.get(
            ENTRIES_URL, params={"projectId": project_id, "type": "entity"}
        )
    ).json()
    assert entity_only["countsByType"] == unfiltered["countsByType"]
    assert entity_only["total"] == unfiltered["countsByType"]["entity"] == 5

    too_large = await client.get(ENTRIES_URL, params={"limit": 201})
    assert too_large.status_code == 400
    assert too_large.json()["code"] == "validation_error"
    too_small = await client.get(ENTRIES_URL, params={"limit": 0})
    assert too_small.status_code == 400

    corrupted = await client.get(ENTRIES_URL, params={"cursor": "not-a-cursor"})
    assert corrupted.status_code == 400
    assert corrupted.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_tc121_entry_detail_contains_all_fields_and_neighbors(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    await _import(
        client,
        project_id,
        [
            {
                "id": "ENT-001",
                "zh_name": "支付单",
                "zh_definition": "一次支付请求",
                "fields": {"order_id": "string"},
                "tables": ["payment_order"],
                "code_paths": ["src/pay/order.py"],
                "neighbors": [
                    {"id": "TERM-001", "relation": "depends_on"},
                    {"id": "ENT-999", "relation": "depends_on"},
                ],
                "source_doc": "payment-domain.md",
                "anchor": "ent-payment-order",
            },
            {"id": "TERM-001", "zh_name": "收单", "zh_definition": "受理支付"},
        ],
        name="详情库",
        docs={"ENT-001.md": "# 支付单\n\n正文".encode("utf-8")},
    )

    entry_id = (await _entry_ids(client, {"projectId": project_id}))["ENT-001"]
    response = await client.get(f"{ENTRIES_URL}/{entry_id}")
    assert response.status_code == 200, response.text
    detail = response.json()

    assert detail["code"] == "ENT-001"
    assert detail["type"] == "entity"
    assert detail["summary"] == "一次支付请求"
    assert detail["body"] == "# 支付单\n\n正文"
    assert detail["bodyMissing"] is False
    assert detail["bodySourceFile"] == "ENT-001.md"
    assert detail["sourceDoc"] == "payment-domain.md"
    assert detail["anchor"] == "ent-payment-order"
    assert detail["fields"] == {"order_id": "string"}
    assert detail["tables"] == ["payment_order"]
    assert detail["codePaths"] == ["src/pay/order.py"]
    assert detail["freshness"] == {"at": None, "state": "unknown"}

    existing, missing = detail["neighbors"]
    assert existing["code"] == "TERM-001"
    assert existing["exists"] is True
    assert existing["entryId"]
    assert existing["kbId"] == detail["kb"]["kbId"]
    assert existing["title"] == "收单"
    assert missing == {"code": "ENT-999", "exists": False}

    not_found = await client.get(f"{ENTRIES_URL}/{'0' * 32}")
    assert not_found.status_code == 404
    assert not_found.json()["code"] == "entry_not_found"


@pytest.mark.asyncio
async def test_tc122_superseded_entry_points_to_latest(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    old_kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "旧摘要"}],
        name="版本库",
    )
    new_kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "新摘要"}],
        name="版本库",
    )

    old_ids = await _entry_ids(client, {"kbId": old_kb["kbId"]})
    detail = (await client.get(f"{ENTRIES_URL}/{old_ids['ENT-001']}")).json()
    assert detail["kb"]["superseded"] is True
    assert detail["kb"]["current"] is False
    assert detail["kb"]["latestKbId"] == new_kb["kbId"]

    base = (await client.get(f"{BASES_URL}/{old_kb['kbId']}")).json()
    assert base["latestKbId"] == new_kb["kbId"]
    assert base["supersededBy"] == {"kbId": new_kb["kbId"], "version": 2}
    assert [item["version"] for item in base["versions"]] == [1, 2]

    versions = (await client.get(f"{BASES_URL}/{old_kb['kbId']}/versions")).json()
    assert versions["latestKbId"] == new_kb["kbId"]
    assert len(versions["items"]) == 2
    assert versions["items"][0]["status"] == "superseded"

    current = (
        await client.get(ENTRIES_URL, params={"projectId": project_id})
    ).json()
    assert {item["kbId"] for item in current["items"]} == {new_kb["kbId"]}

    scoped = (
        await client.get(f"{BASES_URL}/{old_kb['kbId']}/entries")
    ).json()
    assert [item["code"] for item in scoped["items"]] == ["ENT-001"]
    assert scoped["items"][0]["kbId"] == old_kb["kbId"]

    missing_kb = await client.get(f"{BASES_URL}/{'0' * 32}")
    assert missing_kb.status_code == 404
    assert missing_kb.json()["code"] == "kb_not_found"


@pytest.mark.asyncio
async def test_tc123_detail_shows_summary_when_body_missing(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "无正文", "zh_definition": "只有摘要"}],
        name="缺正文库",
    )

    entry_id = (await _entry_ids(client, {"projectId": project_id}))["ENT-001"]
    detail = (await client.get(f"{ENTRIES_URL}/{entry_id}")).json()
    assert detail["bodyMissing"] is True
    assert detail["body"] is None
    assert detail["summary"] == "只有摘要"


@pytest.mark.asyncio
async def test_tc124_computes_freshness_states(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    now = datetime.now(timezone.utc)
    stale_at = (now - timedelta(days=45)).strftime("%Y-%m-%dT%H:%M:%SZ")
    fresh_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "未知", "zh_definition": "没有时间"},
            {
                "id": "ENT-002",
                "zh_name": "过期",
                "zh_definition": "45 天前",
                "freshness_at": stale_at,
            },
            {
                "id": "ENT-003",
                "zh_name": "新鲜",
                "zh_definition": "刚刚",
                "freshness_at": fresh_at,
            },
        ],
        name="新鲜度库",
    )

    ids = await _entry_ids(client, {"projectId": project_id})
    unknown = (await client.get(f"{ENTRIES_URL}/{ids['ENT-001']}")).json()
    stale = (await client.get(f"{ENTRIES_URL}/{ids['ENT-002']}")).json()
    fresh = (await client.get(f"{ENTRIES_URL}/{ids['ENT-003']}")).json()

    assert unknown["freshness"] == {"at": None, "state": "unknown"}
    assert stale["freshness"]["state"] == "stale"
    assert stale["freshness"]["at"] == stale_at
    assert fresh["freshness"]["state"] == "fresh"
    assert fresh["freshness"]["at"] == fresh_at


@pytest.mark.asyncio
async def test_tc125_detects_conflict_by_summary_digest(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    kb_a = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "摘要A"}],
        name="冲突库A",
    )
    kb_b = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "摘要B"}],
        name="冲突库B",
    )
    kb_c = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "摘要A"}],
        name="冲突库C",
    )

    listing = (
        await client.get(ENTRIES_URL, params={"projectId": project_id})
    ).json()
    assert all(item["conflict"]["hasConflict"] is True for item in listing["items"])
    assert len(listing["items"]) == 3

    ids = await _entry_ids(
        client, {"projectId": project_id, "kbId": kb_a["kbId"]}
    )
    detail = (await client.get(f"{ENTRIES_URL}/{ids['ENT-001']}")).json()
    sources = {
        (item["kbName"], item["version"]) for item in detail["conflicts"]
    }
    assert sources == {("冲突库B", 1)}
    assert set(detail["conflicts"][0]) == {"kbName", "version", "generatedAt"}

    same_digest = await _entry_ids(
        client, {"projectId": project_id, "kbId": kb_c["kbId"]}
    )
    other_digest = await _entry_ids(
        client, {"projectId": project_id, "kbId": kb_b["kbId"]}
    )
    same_detail = (
        await client.get(f"{ENTRIES_URL}/{same_digest['ENT-001']}")
    ).json()
    other_detail = (
        await client.get(f"{ENTRIES_URL}/{other_digest['ENT-001']}")
    ).json()
    assert {item["kbName"] for item in same_detail["conflicts"]} == {"冲突库B"}
    assert {item["kbName"] for item in other_detail["conflicts"]} == {
        "冲突库A",
        "冲突库C",
    }

    await _seed_extra_conflicts(database.sessionmaker, project_id, count=21)
    capped = (await client.get(f"{ENTRIES_URL}/{ids['ENT-001']}")).json()
    assert len(capped["conflicts"]) == 20


async def _seed_extra_conflicts(sessionmaker, project_id: int, *, count: int) -> None:  # noqa: ANN001
    now = utcnow()
    async with sessionmaker() as db:
        for index in range(count):
            kb_id = uuid4().hex
            summary = f"冲突摘要{index}"
            db.add(
                KnowledgeBase(
                    kb_id=kb_id,
                    project_id=project_id,
                    name=f"直接冲突库{index}",
                    name_key=f"直接冲突库{index}".casefold(),
                    version=1,
                    current_flag="1",
                    status="ready",
                    entry_count=1,
                    file_count=1,
                    total_byte_size=1,
                    source_index_sha256="0" * 64,
                    storage_dir=f"knowledge-bases/{kb_id}",
                    created_at=now,
                    updated_at=now,
                )
            )
            db.add(
                KnowledgeEntry(
                    kb_id=kb_id,
                    code="ENT-001",
                    code_key="ent-001",
                    type="entity",
                    title="支付单",
                    summary=summary,
                    body_missing=True,
                    content_digest=summary_digest(summary),
                    created_at=now,
                )
            )
        await db.commit()


@pytest.mark.asyncio
async def test_tc126_conflict_query_is_batched(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)
    await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "实体一", "zh_definition": "a"},
            {"id": "ENT-002", "zh_name": "实体二", "zh_definition": "b"},
        ],
        name="批量库一",
    )
    service = KnowledgeQueryService(sessionmaker=database.sessionmaker)

    first = await _count_selects(database.engine, service, project_id)
    await _import(
        client,
        project_id,
        [
            {"id": f"TERM-00{index}", "zh_name": f"术语{index}", "zh_definition": "c"}
            for index in range(1, 6)
        ],
        name="批量库二",
    )
    second = await _count_selects(database.engine, service, project_id)

    assert first <= 3
    assert first == second


async def _count_selects(engine, service: KnowledgeQueryService, project_id: int) -> int:  # noqa: ANN001
    statements: list[str] = []

    def before(  # noqa: ANN001
        conn, cursor, statement, parameters, context, executemany
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", before)
    try:
        result = await service.search_entries(project_id=project_id, limit=50)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before)
    assert result["items"]
    return len(statements)


@pytest.mark.asyncio
async def test_tc143_project_summary_returns_zero_to_n_bases(api) -> None:
    client, database, _settings = api
    project_id = await seed_project(database.sessionmaker)

    empty = (await client.get(BASES_URL, params={"projectId": project_id})).json()
    assert empty["items"] == []
    assert empty["nextCursor"] is None

    first = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "一", "zh_definition": "a"}],
        name="摘要库一",
    )
    second = await _import(
        client,
        project_id,
        [{"id": "ENT-002", "zh_name": "二", "zh_definition": "b"}],
        name="摘要库二",
    )
    await _set_updated_at(
        database.sessionmaker,
        {first["kbId"]: "2026-01-01T00:00:00", second["kbId"]: "2026-02-01T00:00:00"},
    )

    listed = (await client.get(BASES_URL, params={"projectId": project_id})).json()
    assert [item["kbId"] for item in listed["items"]] == [
        second["kbId"],
        first["kbId"],
    ]
    assert all(item["status"] == "ready" for item in listed["items"])
    assert listed["items"][0]["latestKbId"] == second["kbId"]
    assert listed["items"][1]["latestKbId"] == first["kbId"]

    missing = await client.get(BASES_URL, params={"projectId": 999_999})
    assert missing.status_code == 404
    assert missing.json()["code"] == "project_not_found"


async def _set_updated_at(sessionmaker, values: dict[str, str]) -> None:  # noqa: ANN001
    async with sessionmaker() as db:
        for kb_id, moment in values.items():
            await db.execute(
                update(KnowledgeBase)
                .where(KnowledgeBase.kb_id == kb_id)
                .values(updated_at=datetime.fromisoformat(moment))
            )
        await db.commit()
