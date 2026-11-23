"""注入预览 / 候选 / 经 core 调用的进程内契约。用例名带 TC 编号。"""

from __future__ import annotations

import inspect
import json
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
from vigil_workbench.core.ports import (
    InjectionPreparer,
    InjectionSnapshot,
    KnowledgeRef,
    get_injection_preparer,
)
from vigil_workbench.db.models import AiCallRecord, SessionEvent
from vigil_workbench.knowledge.config import get_kb_settings
from vigil_workbench.knowledge.errors import KnowledgeInvalidEntriesError
from vigil_workbench.services.ai_gateway import AiGateway
from vigil_workbench.services.knowledge.injection_service import KnowledgeInjectionService
from vigil_workbench.services.knowledge.registration import (
    install_injection_preparer,
    uninstall_injection_preparer,
)

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"
CANDIDATES_URL = "/api/v1/sessions/{session_id}/knowledge-injection/candidates"
PREVIEW_URL = "/api/v1/sessions/{session_id}/knowledge-injection/preview"
COMPLETE_URL = "/api/v1/sessions/{session_id}/ai/complete"

SENTINEL_BODY = "哨兵正文-4b17-不得入库"


class FakeAdapter:
    def __init__(self, *, text: str = "模型回答") -> None:
        self.text = text
        self.calls: list[dict[str, Any]] = []

    async def complete(self, **kwargs):  # noqa: ANN003, ANN201
        self.calls.append(kwargs)
        return self.text

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


def make_index(
    entries: list[dict[str, Any]],
    *,
    name: str = "支付域知识库",
) -> bytes:
    document = {"schema": "knowledge/v1", "name": name, "entries": entries}
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
    adapter = FakeAdapter()
    app = make_app(
        settings=settings,
        database=database,
        ai_gateway=AiGateway(adapter=adapter, retry_backoff=0),
    )
    install_injection_preparer(app)
    try:
        async with build_client(app) as client:
            login = await client.post(
                "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
            )
            assert login.status_code == 200
            yield client, database, settings, adapter
    finally:
        uninstall_injection_preparer()


async def _import(
    client,  # noqa: ANN001
    project_id: int,
    entries: list[dict[str, Any]],
    *,
    name: str = "支付域知识库",
    docs: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    response = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": name},
        files=_files(make_index(entries, name=name), docs),
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["kb"]


async def _counts(sm) -> tuple[int, int]:  # noqa: ANN001
    async with sm() as db:
        calls = await db.scalar(select(func.count()).select_from(AiCallRecord))
        events = await db.scalar(select(func.count()).select_from(SessionEvent))
    return int(calls or 0), int(events or 0)


@pytest.mark.asyncio
async def test_tc129_preview_reports_segments_and_over_limit(api) -> None:
    client, database, settings, _adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        docs={"ENT-001.md": ("正文" * 100).encode("utf-8")},
    )

    response = await client.post(
        PREVIEW_URL.format(session_id=session_id),
        json={"refs": [{"kbId": kb["kbId"], "code": "ENT-001"}], "userPrompt": "请分析"},
        headers=ORIGIN,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["promptChars"] == len("请分析")
    assert body["injectedChars"] > 0
    assert body["totalChars"] == body["promptChars"] + body["injectedChars"]
    assert body["limit"] == settings.prompt_max_chars
    assert body["overLimit"] is False
    assert body["invalidItems"] == []
    assert body["warnings"] == []
    item = body["items"][0]
    assert item["kbId"] == kb["kbId"]
    assert item["kbName"] == "支付域知识库"
    assert item["kbVersion"] == 1
    assert item["source"] == "body"
    assert item["chars"] > 0
    # 预览只回标识与字数，不回注入文本。
    assert "正文" * 100 not in response.text

    settings.prompt_max_chars = 10
    over = await client.post(
        PREVIEW_URL.format(session_id=session_id),
        json={"refs": [{"kbId": kb["kbId"], "code": "ENT-001"}], "userPrompt": "请分析"},
        headers=ORIGIN,
    )
    assert over.status_code == 200
    over_body = over.json()
    assert over_body["overLimit"] is True
    assert over_body["limit"] == 10
    assert over_body["injectedChars"] == body["injectedChars"]
    assert await _counts(database.sessionmaker) == (0, 0)


@pytest.mark.asyncio
async def test_tc131_invalid_entries_block_call_without_record(api) -> None:
    client, database, settings, adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    old = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "旧版", "zh_definition": "旧定义"}],
        name="库",
    )
    await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "新版", "zh_definition": "新定义"}],
        name="库",
    )

    refs = [{"kbId": old["kbId"], "entryCodes": ["ENT-001"]}]
    response = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={"prompt": "请分析", "knowledgeRefs": refs},
        headers=ORIGIN,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "knowledge_invalid_entries"
    assert response.json()["details"]["invalidItems"] == [
        {"kbId": old["kbId"], "code": "ENT-001", "reason": "superseded"}
    ]
    assert await _counts(database.sessionmaker) == (0, 0)
    assert adapter.calls == []

    # 服务层同一判定：不确认即阻塞，错误详情完整。
    service = KnowledgeInjectionService(
        sessionmaker=database.sessionmaker,
        kb_settings=get_kb_settings(),
        settings=settings,
    )
    with pytest.raises(KnowledgeInvalidEntriesError) as caught:
        await service.prepare_for_call(
            session_id=session_id,
            project_id=project_id,
            prompt="请分析",
            knowledge_refs=[
                KnowledgeRef(kb_id=old["kbId"], entry_codes=("ENT-001",))
            ],
            confirm_invalid_codes=(),
        )
    assert caught.value.details == {
        "invalidItems": [
            {"kbId": old["kbId"], "code": "ENT-001", "reason": "superseded"}
        ]
    }


@pytest.mark.asyncio
async def test_tc132_confirmation_requires_exact_invalid_set(api) -> None:
    client, database, _settings, _adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"},
            {"id": "ENT-002", "zh_name": "退款单", "zh_definition": "一次退款请求"},
        ],
        docs={"ENT-002.md": "退款正文".encode("utf-8")},
    )
    kb_id = kb["kbId"]
    refs = [{"kbId": kb_id, "entryCodes": ["ENT-002", "ENT-404", "ENT-405"]}]

    async def post(confirm: list[dict[str, str]]) -> Any:  # noqa: ANN202
        return await client.post(
            COMPLETE_URL.format(session_id=session_id),
            json={
                "prompt": "请分析",
                "knowledgeRefs": refs,
                "confirmInvalidCodes": confirm,
            },
            headers=ORIGIN,
        )

    missing = await post([{"kbId": kb_id, "code": "ENT-404"}])
    assert missing.status_code == 409
    assert len(missing.json()["details"]["invalidItems"]) == 2

    extra = await post(
        [
            {"kbId": kb_id, "code": "ENT-404"},
            {"kbId": kb_id, "code": "ENT-405"},
            {"kbId": kb_id, "code": "ENT-999"},
        ]
    )
    assert extra.status_code == 409
    assert await _counts(database.sessionmaker) == (0, 0)

    # 顺序不同但集合完全相等 → 继续并写快照。
    exact = await post(
        [
            {"kbId": kb_id, "code": "ENT-405"},
            {"kbId": kb_id, "code": "ENT-404"},
        ]
    )
    assert exact.status_code == 200, exact.text
    body = exact.json()
    assert body["knowledgeInjection"][0]["entryCodes"] == ["ENT-002"]
    assert body["knowledgeInjection"][0]["kbId"] == kb_id
    async with database.sessionmaker() as db:
        record = await db.get(AiCallRecord, body["callId"])
        assert record is not None
        events = list(
            await db.scalars(
                select(SessionEvent).where(SessionEvent.session_id == session_id)
            )
        )
        assert "knowledge_injection" in [event.type for event in events]


@pytest.mark.asyncio
async def test_tc133_cancel_does_not_initiate_call(api) -> None:
    client, database, _settings, adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "旧版", "zh_definition": "旧定义"}],
        name="库",
    )
    await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "新版", "zh_definition": "新定义"}],
        name="库",
    )

    response = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={
            "prompt": "请分析",
            "knowledgeRefs": [
                {"kbId": "0" * 32, "entryCodes": ["ENT-001"]}
            ],
        },
        headers=ORIGIN,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "knowledge_invalid_entries"
    # 用户取消：不再重试，因此没有调用记录、事件或网关请求。
    assert await _counts(database.sessionmaker) == (0, 0)
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_tc136_records_injection_snapshot_without_body(api) -> None:
    client, database, _settings, adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        docs={"ENT-001.md": SENTINEL_BODY.encode("utf-8")},
    )

    response = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={
            "prompt": "请分析",
            "knowledgeRefs": [
                {"kbId": kb["kbId"], "entryCodes": ["ENT-001"]}
            ],
        },
        headers=ORIGIN,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    # 模型确实收到了正文，但留痕不能复制正文。
    assert SENTINEL_BODY in adapter.calls[0]["prepared"]

    injected = body["knowledgeInjection"]
    assert [item["kbId"] for item in injected] == [kb["kbId"]]
    assert injected[0]["entryCodes"] == ["ENT-001"]
    assert injected[0]["kbName"] == "支付域知识库"
    assert injected[0]["kbVersion"] == 1
    assert injected[0]["injectedChars"] > 0

    async with database.sessionmaker() as db:
        record = await db.get(AiCallRecord, body["callId"])
        assert record is not None
        assert record.prompt_chars == len("请分析")
        assert record.total_chars == len(adapter.calls[0]["prepared"])
        assert record.injected_chars == record.total_chars - record.prompt_chars
        assert isinstance(record.knowledge_injection, list)
        assert SENTINEL_BODY not in json.dumps(
            record.knowledge_injection, ensure_ascii=False
        )
        event = await db.scalar(
            select(SessionEvent).where(
                SessionEvent.session_id == session_id,
                SessionEvent.type == "knowledge_injection",
            )
        )
        assert event is not None
        assert event.payload["items"][0]["entryCodes"] == ["ENT-001"]
        assert SENTINEL_BODY not in json.dumps(event.payload, ensure_ascii=False)


def test_tc136_prepare_for_call_matches_core_protocol() -> None:
    signature = inspect.signature(KnowledgeInjectionService.prepare_for_call)
    protocol = inspect.signature(InjectionPreparer.prepare_for_call)
    assert list(signature.parameters) == list(protocol.parameters)
    for name in (
        "session_id",
        "project_id",
        "prompt",
        "knowledge_refs",
        "confirm_invalid_codes",
    ):
        assert (
            signature.parameters[name].kind
            is inspect.Parameter.KEYWORD_ONLY
        )

    assert set(InjectionSnapshot.__dataclass_fields__) == {
        "items",
        "prompt_chars",
        "injected_chars",
        "total_chars",
        "excluded_codes",
    }


@pytest.mark.asyncio
async def test_tc136_lifespan_registers_real_preparer(api) -> None:
    _client, database, settings, _adapter = api
    uninstall_injection_preparer()
    app = make_app(settings=settings, database=database)
    assert get_injection_preparer() is None
    async with app.router.lifespan_context(app):
        assert isinstance(get_injection_preparer(), KnowledgeInjectionService)
    assert get_injection_preparer() is None


@pytest.mark.asyncio
async def test_tc138_candidates_only_current_versions_with_badges(api) -> None:
    client, database, _settings, _adapter = api
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)
    await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "旧实体", "zh_definition": "旧定义"},
            {"id": "ENT-002", "zh_name": "旧退款", "zh_definition": "旧退款定义"},
        ],
        name="库A",
    )
    current = await _import(
        client,
        project_id,
        [
            {"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"},
            {"id": "TERM-001", "zh_name": "收单", "zh_definition": "受理支付"},
        ],
        name="库A",
        docs={"ENT-001.md": "正文".encode("utf-8")},
    )
    doomed = await _import(
        client,
        project_id,
        [{"id": "ENT-900", "zh_name": "待删", "zh_definition": "待删定义"}],
        name="库B",
    )
    deleted = await client.delete(
        f"/api/v1/knowledge-bases/{doomed['kbId']}", headers=ORIGIN
    )
    assert deleted.status_code == 204

    response = await client.get(CANDIDATES_URL.format(session_id=session_id))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["projectId"] == project_id
    codes = {item["code"] for item in body["items"]}
    assert codes == {"ENT-001", "TERM-001"}
    assert all(item["kbId"] == current["kbId"] for item in body["items"])
    assert all(item["superseded"] is False for item in body["items"])
    for item in body["items"]:
        assert {"freshness", "conflict", "bodyMissing"} <= set(item)
    assert body["countsByType"]["entity"] == 1

    filtered = await client.get(
        CANDIDATES_URL.format(session_id=session_id),
        params={"type": "term", "limit": 1},
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert [item["code"] for item in filtered_body["items"]] == ["TERM-001"]
    assert filtered_body["total"] == 1

    missing = await client.get(CANDIDATES_URL.format(session_id=999_999))
    assert missing.status_code == 404
    assert missing.json()["code"] == "session_not_found"
