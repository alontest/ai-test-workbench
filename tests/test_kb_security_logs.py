"""内容安全：日志、错误体与留痕都不含正文（ADR-114）。用例名带 TC 编号。"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
import pytest_asyncio

from helpers import build_client, make_app, seed_admin, seed_session_graph
from vigil_workbench.services.ai_gateway import AiGateway
from vigil_workbench.services.knowledge.registration import (
    install_injection_preparer,
    uninstall_injection_preparer,
)

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"
PREVIEW_URL = "/api/v1/sessions/{session_id}/knowledge-injection/preview"
COMPLETE_URL = "/api/v1/sessions/{session_id}/ai/complete"

SENTINEL_BODY = "哨兵正文-6d0a-绝不外泄的内部实现"


class FakeAdapter:
    async def complete(self, **kwargs):  # noqa: ANN003, ANN201
        return "模型回答"

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


def make_index(entries: list[dict[str, Any]], *, name: str = "库") -> bytes:
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


def _enable_workbench_logging() -> None:
    """Alembic 的 fileConfig 会禁用既有 logger；本用例需重新打开应用日志。"""
    for name, item in logging.Logger.manager.loggerDict.items():
        if name == "vigil_workbench" or name.startswith("vigil_workbench."):
            if isinstance(item, logging.Logger):
                item.disabled = False


def _assert_clean(caplog, response) -> None:  # noqa: ANN001
    assert SENTINEL_BODY not in response.text
    assert SENTINEL_BODY not in caplog.text


@pytest.mark.asyncio
async def test_tc137_logs_and_errors_never_contain_body(api, caplog) -> None:
    client, database, settings = api
    _enable_workbench_logging()
    # 只观察应用日志；驱动层（aiosqlite）的 SQL 参数日志不属 ADR-114 范围。
    caplog.set_level("DEBUG", logger="vigil_workbench")
    project_id, _model_id, session_id = await seed_session_graph(database.sessionmaker)

    # 导入成功路径：导入报告只含原因码与计数。
    imported = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": "库"},
        files=_files(
            make_index(
                [
                    {
                        "id": "ENT-001",
                        "zh_name": "支付单",
                        "zh_definition": "一次支付请求",
                    }
                ]
            ),
            {"ENT-001.md": SENTINEL_BODY.encode("utf-8")},
        ),
        headers=ORIGIN,
    )
    assert imported.status_code == 201
    assert SENTINEL_BODY not in json.dumps(
        imported.json()["importReport"], ensure_ascii=False
    )
    _assert_clean(caplog, imported)
    old_kb_id = imported.json()["kb"]["kbId"]

    # 同名再导让旧版本失效，供注入失败路径使用。
    current = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": "库"},
        files=_files(
            make_index(
                [
                    {
                        "id": "ENT-001",
                        "zh_name": "支付单",
                        "zh_definition": "一次支付请求",
                    }
                ]
            ),
            {"ENT-001.md": SENTINEL_BODY.encode("utf-8")},
        ),
        headers=ORIGIN,
    )
    assert current.status_code == 201
    _assert_clean(caplog, current)
    current_kb_id = current.json()["kb"]["kbId"]

    invalid = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={
            "prompt": "请分析",
            "knowledgeRefs": [{"kbId": old_kb_id, "entryCodes": ["ENT-001"]}],
        },
        headers=ORIGIN,
    )
    assert invalid.status_code == 409
    assert invalid.json()["details"]["invalidItems"] == [
        {"kbId": old_kb_id, "code": "ENT-001", "reason": "superseded"}
    ]
    _assert_clean(caplog, invalid)

    # 超预算错误只带分段字数。
    settings.prompt_max_chars = 10
    over_budget = await client.post(
        COMPLETE_URL.format(session_id=session_id),
        json={
            "prompt": "请分析",
            "knowledgeRefs": [{"kbId": current_kb_id, "entryCodes": ["ENT-001"]}],
        },
        headers=ORIGIN,
    )
    assert over_budget.status_code == 400
    assert over_budget.json()["code"] == "prompt_budget_exceeded"
    assert set(over_budget.json()["details"]) == {
        "promptChars",
        "injectedChars",
        "totalChars",
        "limit",
    }
    _assert_clean(caplog, over_budget)

    preview = await client.post(
        PREVIEW_URL.format(session_id=session_id),
        json={
            "refs": [{"kbId": current_kb_id, "code": "ENT-001"}],
            "userPrompt": "请分析",
        },
        headers=ORIGIN,
    )
    assert preview.status_code == 200
    assert preview.json()["overLimit"] is True
    _assert_clean(caplog, preview)

    # 解析失败路径：错误体只回错误码与行号。
    broken_index = (
        '{"schema": "knowledge/v1", "entries": ['
        f'{{"id": "ENT-001", "zh_definition": "{SENTINEL_BODY}"}}'
    ).encode("utf-8")
    broken = await client.post(
        IMPORT_URL,
        data={"projectId": str(project_id), "name": "坏库"},
        files=_files(broken_index, {"ENT-001.md": SENTINEL_BODY.encode("utf-8")}),
        headers=ORIGIN,
    )
    assert broken.status_code == 400
    assert broken.json()["code"] == "index_json_invalid"
    _assert_clean(caplog, broken)
