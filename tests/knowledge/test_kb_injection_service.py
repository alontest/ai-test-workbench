"""知识注入服务：预算、失效分类、警告不阻断。用例名带 TC 编号。"""

from __future__ import annotations

import json
from typing import Any

import pytest
import pytest_asyncio

from helpers import build_client, make_app, seed_admin, seed_project
from vigil_workbench.core.ports import InvalidCodeRef, KnowledgeRef
from vigil_workbench.knowledge.config import get_kb_settings
from vigil_workbench.knowledge.errors import (
    KnowledgeInjectionEmptyError,
    KnowledgeInvalidEntriesError,
    PromptBudgetExceededError,
)
from vigil_workbench.services.knowledge.injection_service import (
    REASON_ENTRY_NOT_FOUND,
    REASON_KB_DELETED,
    REASON_SUPERSEDED,
    KnowledgeInjectionService,
)

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
IMPORT_URL = "/api/v1/knowledge-bases"

SENTINEL_BODY = "哨兵正文-8f2c-不得进日志"


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


def _service(database, settings) -> KnowledgeInjectionService:  # noqa: ANN001
    return KnowledgeInjectionService(
        sessionmaker=database.sessionmaker,
        kb_settings=get_kb_settings(),
        settings=settings,
    )


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


async def _superseded_kb(
    client, project_id: int, *, name: str = "库", code: str = "ENT-001"
) -> dict[str, Any]:
    first = await _import(
        client,
        project_id,
        [{"id": code, "zh_name": "旧版", "zh_definition": "旧定义"}],
        name=name,
    )
    second = await _import(
        client,
        project_id,
        [{"id": code, "zh_name": "新版", "zh_definition": "新定义"}],
        name=name,
    )
    return {"old": first, "new": second}


@pytest.mark.asyncio
async def test_tc130_rejects_over_budget_without_truncation(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "一次支付请求"}],
        docs={"ENT-001.md": ("正文" * 400).encode("utf-8")},
    )

    service = _service(database, settings)
    refs = [KnowledgeRef(kb_id=kb["kbId"], entry_codes=("ENT-001",))]
    preview = await service.preview(
        project_id=project_id, refs=refs, user_prompt="请分析"
    )
    assert preview["injectedChars"] > 0
    assert preview["items"][0]["chars"] > 0
    assert preview["overLimit"] is False

    # 字数按与 preview 相同的组装口径计算，误差不得来自截断。
    settings.prompt_max_chars = preview["injectedChars"] + preview["promptChars"] - 1
    with pytest.raises(PromptBudgetExceededError) as caught:
        await service.prepare_for_call(
            session_id=1,
            project_id=project_id,
            prompt="请分析",
            knowledge_refs=refs,
            confirm_invalid_codes=(),
        )
    assert caught.value.code == "prompt_budget_exceeded"
    assert caught.value.details == {
        "promptChars": preview["promptChars"],
        "injectedChars": preview["injectedChars"],
        "totalChars": preview["totalChars"],
        "limit": settings.prompt_max_chars,
    }


@pytest.mark.asyncio
async def test_tc134_confirmation_with_empty_valid_set_is_rejected(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    versions = await _superseded_kb(client, project_id)
    old = versions["old"]

    service = _service(database, settings)
    refs = [KnowledgeRef(kb_id=old["kbId"], entry_codes=("ENT-001",))]
    confirms = [InvalidCodeRef(kb_id=old["kbId"], code="ENT-001")]

    with pytest.raises(KnowledgeInjectionEmptyError) as caught:
        await service.prepare_for_call(
            session_id=1,
            project_id=project_id,
            prompt="请分析",
            knowledge_refs=refs,
            confirm_invalid_codes=confirms,
        )
    assert caught.value.code == "knowledge_injection_empty"
    assert caught.value.status_code == 409


@pytest.mark.asyncio
async def test_tc135_classifies_invalid_reasons(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    versions = await _superseded_kb(client, project_id)
    old = versions["old"]
    current = versions["new"]
    missing_kb_id = "f" * 32

    service = _service(database, settings)
    refs = [
        KnowledgeRef(kb_id=old["kbId"], entry_codes=("ENT-001",)),
        KnowledgeRef(kb_id=current["kbId"], entry_codes=("ENT-404",)),
        KnowledgeRef(kb_id=missing_kb_id, entry_codes=("ENT-001",)),
    ]
    preview = await service.preview(
        project_id=project_id, refs=refs, user_prompt="请分析"
    )
    reasons = {
        (item["kbId"], item["code"]): item["reason"]
        for item in preview["invalidItems"]
    }
    assert reasons == {
        (missing_kb_id, "ENT-001"): REASON_KB_DELETED,
        (current["kbId"], "ENT-404"): REASON_ENTRY_NOT_FOUND,
        (old["kbId"], "ENT-001"): REASON_SUPERSEDED,
    }
    assert preview["items"] == []
    assert preview["invalidItems"] == sorted(
        preview["invalidItems"], key=lambda item: (item["kbId"], item["code"])
    )

    with pytest.raises(KnowledgeInvalidEntriesError) as caught:
        await service.prepare_for_call(
            session_id=1,
            project_id=project_id,
            prompt="请分析",
            knowledge_refs=refs,
            confirm_invalid_codes=(),
        )
    assert caught.value.details == {"invalidItems": preview["invalidItems"]}


@pytest.mark.asyncio
async def test_tc149_freshness_and_conflict_warnings_do_not_block(api) -> None:
    client, database, settings = api
    project_id = await seed_project(database.sessionmaker)
    kb = await _import(
        client,
        project_id,
        [
            {
                "id": "ENT-001",
                "zh_name": "支付单",
                "zh_definition": "一次支付请求",
                "freshness_at": "2026-01-01T00:00:00Z",
            }
        ],
        name="库A",
        docs={"ENT-001.md": SENTINEL_BODY.encode("utf-8")},
    )
    await _import(
        client,
        project_id,
        [{"id": "ENT-001", "zh_name": "支付单", "zh_definition": "另一份定义"}],
        name="库B",
        docs={"ENT-001.md": "另一份正文".encode("utf-8")},
    )

    service = _service(database, settings)
    refs = [KnowledgeRef(kb_id=kb["kbId"], entry_codes=("ENT-001",))]
    preview = await service.preview(
        project_id=project_id, refs=refs, user_prompt="请分析"
    )
    kinds = {warning["kind"] for warning in preview["warnings"]}
    assert {"stale", "conflict"} <= kinds
    assert preview["overLimit"] is False

    prepared = await service.prepare_for_call(
        session_id=1,
        project_id=project_id,
        prompt="请分析",
        knowledge_refs=refs,
        confirm_invalid_codes=(),
    )
    assert prepared.prepared.endswith("请分析")
    assert SENTINEL_BODY in prepared.prepared
    assert prepared.snapshot.excluded_codes == ()
    assert prepared.snapshot.total_chars == len(prepared.prepared)
