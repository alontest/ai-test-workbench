"""自动上下文推荐、两阶段生成、Stale 复核与导出 API 测试（TC-309 ~ TC-317）。"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
)
from workbench.db.base import utcnow
from workbench.db.models import (
    AiCallRecord,
    AnalysisSession,
    KnowledgeBase,
    KnowledgeEntry,
    RepoBinding,
    RepoFileReadRecord,
    SessionEvent,
    TestCase,
)
from workbench.services.ai_gateway import AiGateway
from workbench.services.skills import BUILTIN_TEST_CASE_SKILL_SLUG

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class ScriptedAdapter:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("模型出口被调用的次数超出预期")
        return self.responses.pop(0)

    async def test_connection(self, **kwargs: Any):  # pragma: no cover
        raise NotImplementedError


async def _login(client) -> None:  # noqa: ANN001
    resp = await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
    assert resp.status_code == 200


async def _seed_kb(
    sessionmaker,  # noqa: ANN001
    project_id: int,
    *,
    name: str,
    entries: list[dict[str, Any]],
) -> str:
    kb_id = uuid4().hex
    now = utcnow()
    async with sessionmaker() as db:
        db.add(
            KnowledgeBase(
                kb_id=kb_id,
                project_id=project_id,
                name=name,
                name_key=name.casefold(),
                version=1,
                current_flag="1",
                status="ready",
                entry_count=len(entries),
                file_count=1,
                total_byte_size=1,
                source_index_sha256="0" * 64,
                storage_dir=f"knowledge-bases/{kb_id}",
                created_at=now,
                updated_at=now,
            )
        )
        for spec in entries:
            code = spec["code"]
            body = spec.get("body")
            db.add(
                KnowledgeEntry(
                    entry_id=uuid4().hex,
                    kb_id=kb_id,
                    code=code,
                    code_key=spec.get("code_key", code.casefold()),
                    type=spec.get("type", "rule"),
                    title=spec["title"],
                    summary=spec.get("summary", ""),
                    body=body,
                    body_missing=body is None,
                    tables=spec.get("tables"),
                    fields=spec.get("fields"),
                    code_paths=spec.get("code_paths"),
                    neighbors=spec.get("neighbors"),
                    content_digest=spec.get("content_digest")
                    or _digest(body or spec.get("summary") or spec["title"]),
                    created_at=now,
                )
            )
        await db.commit()
    return kb_id


async def _seed_repo_reads(
    sessionmaker,  # noqa: ANN001
    project_id: int,
    reads: list[tuple[str, str]],
) -> str:
    binding_id = uuid4().hex
    now = utcnow()
    async with sessionmaker() as db:
        db.add(
            RepoBinding(
                binding_id=binding_id,
                project_id=project_id,
                provider="github",
                api_base_url="https://api.github.com",
                repo_name="pay/checkout",
                repo_key="pay/checkout",
                display_name="checkout",
                status="connected",
                active_flag="1",
                created_at=now,
                updated_at=now,
            )
        )
        for path, status in reads:
            db.add(
                RepoFileReadRecord(
                    read_id=uuid4().hex,
                    binding_id=binding_id,
                    repo_id="pay/checkout",
                    ref="main",
                    file_path=path,
                    encoding="text",
                    status=status,
                    fetched_at=now,
                )
            )
        await db.commit()
    return binding_id


async def _seed_case(
    sessionmaker,  # noqa: ANN001
    project_id: int,
    *,
    case_code: str,
    module: str,
    title: str,
    kb_links: list[dict[str, str]],
    code_paths: list[str] | None = None,
    priority: str = "P1",
) -> str:
    case_id = uuid4().hex
    now = utcnow()
    async with sessionmaker() as db:
        db.add(
            TestCase(
                case_id=case_id,
                project_id=project_id,
                case_code=case_code,
                module=module,
                title=title,
                priority=priority,
                case_type="functional",
                preconditions=[],
                steps=[{"stepNo": 1, "action": "执行", "expected": "通过"}],
                expected_summary="符合预期",
                kb_links=list(kb_links),
                code_paths=list(code_paths or []),
                created_at=now,
                updated_at=now,
            )
        )
        await db.commit()
    return case_id


def _anchor(
    kb_id: str,
    kb_name: str,
    code: str,
    title: str,
    digest: str,
) -> dict[str, str]:
    return {
        "kbId": kb_id,
        "kbNameKey": kb_name.casefold(),
        "code": code,
        "codeKey": code.casefold(),
        "title": title,
        "contentDigest": digest,
    }


def _checkpoints_payload() -> str:
    return (
        "```json\n"
        '{"checkpoints": ['
        '{"checkpointId": "CP-01", "module": "订单中心/超时关单", '
        '"scenario": "订单超时后自动关闭", "category": "functional", '
        '"priority": "P0", "rationale": "引用 BR-001", '
        '"kbCodes": ["BR-001"], "codePaths": ["src/order/close.py"]},'
        '{"checkpointId": "CP-02", "module": "订单中心/超时关单", '
        '"scenario": "退款补偿幂等", "category": "security", '
        '"priority": "P2", "rationale": "引用 BR-002", '
        '"kbCodes": ["BR-002"], "codePaths": []}'
        "]}\n"
        "```"
    )


# ---------------------------------------------------------------------------
# TC-309 / TC-310：自动上下文推荐
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tc309_context_recommendation_scores_kb_entries_and_expands_one_hop_neighbors(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "订单中心")
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="order-domain",
        entries=[
            {
                "code": "BR-001",
                "title": "订单超时关闭规则",
                "summary": "订单在超时后自动关闭",
                "tables": ["orders"],
                "fields": ["status"],
                "code_paths": ["src/order/close.py"],
                "neighbors": ["BR-002"],
            },
            {
                "code": "BR-002",
                "title": "退款补偿说明",
                "summary": "财务异步退款",
            },
            {
                "code": "BR-003",
                "title": "库存盘点流程",
                "summary": "每日盘点库存数量",
            },
        ],
    )
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)
        resp = await client.post(
            f"/api/v1/projects/{project_id}/context-recommendations",
            headers=ORIGIN,
            json={
                "text": "请检查 BR-001 订单超时关闭规则在 orders 表更新失败时是否会漏关单",
                "limit": 8,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        entries = body["recommendedKbEntries"]

        primary = entries[0]
        assert primary["code"] == "BR-001"
        assert primary["kbId"] == kb_id
        assert primary["kbName"] == "order-domain"
        assert primary["kbNameKey"] == "order-domain"
        assert primary["matchSource"] == "direct"
        assert primary["viaCode"] is None
        assert primary["score"] >= 170
        assert len(primary["contentDigest"]) == 64

        neighbor = next(item for item in entries if item["code"] == "BR-002")
        assert neighbor["matchSource"] == "neighbor_1hop"
        assert neighbor["viaCode"] == "BR-001"
        assert neighbor["score"] == max(10, primary["score"] // 2)

        assert all(item["code"] != "BR-003" for item in entries)

        limited = await client.post(
            f"/api/v1/projects/{project_id}/context-recommendations",
            headers=ORIGIN,
            json={"text": "BR-001 订单超时关闭规则", "limit": 1},
        )
        assert limited.status_code == 200
        assert [item["code"] for item in limited.json()["recommendedKbEntries"]] == [
            "BR-001"
        ]

        blank = await client.post(
            f"/api/v1/projects/{project_id}/context-recommendations",
            headers=ORIGIN,
            json={"text": "   "},
        )
        assert blank.status_code == 400
        assert blank.json()["code"] == "validation_error"

        missing = await client.post(
            "/api/v1/projects/999999/context-recommendations",
            headers=ORIGIN,
            json={"text": "BR-001"},
        )
        assert missing.status_code == 404
        assert missing.json()["code"] == "project_not_found"

    async with database.sessionmaker() as db:
        call_count = await db.scalar(select(func.count()).select_from(AiCallRecord))
    assert call_count == 0  # 零 LLM 成本


@pytest.mark.asyncio
async def test_tc310_context_recommendation_recalls_code_paths_from_three_sources(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "支付中心")
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="pay-domain",
        entries=[
            {
                "code": "BR-001",
                "title": "支付超时关单规则",
                "summary": "支付超时后关单",
                "code_paths": ["src/order/close.py"],
            }
        ],
    )
    binding_id = await _seed_repo_reads(
        database.sessionmaker,
        project_id,
        [
            ("app/service/OrderService.java", "success"),
            ("src/order/close.py", "success"),
            ("ignored/Binary.java", "refused"),
        ],
    )
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)
        resp = await client.post(
            f"/api/v1/projects/{project_id}/context-recommendations",
            headers=ORIGIN,
            json={
                "text": (
                    "排查 BR-001，重点看 src/payment/RefundService.ts "
                    "与 app/service/OrderService.java"
                )
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert [item["code"] for item in body["recommendedKbEntries"]] == ["BR-001"]
        assert body["recommendedKbEntries"][0]["kbId"] == kb_id

        paths = {item["path"]: item for item in body["recommendedCodePaths"]}
        assert set(paths) == {
            "src/order/close.py",
            "app/service/OrderService.java",
            "src/payment/RefundService.ts",
        }

        kb_path = paths["src/order/close.py"]
        assert kb_path["source"] == "kb_code_path"
        assert kb_path["linkedKbCodes"] == ["BR-001"]
        assert kb_path["bindingId"] == binding_id

        recent = paths["app/service/OrderService.java"]
        assert recent["source"] == "recent_repo_read"
        assert recent["bindingId"] == binding_id
        assert recent["linkedKbCodes"] == []

        mention = paths["src/payment/RefundService.ts"]
        assert mention["source"] == "input_path_mention"
        assert mention["linkedKbCodes"] == []
        assert mention["bindingId"] is None


# ---------------------------------------------------------------------------
# TC-311 / TC-312 / TC-313：两阶段生成
# ---------------------------------------------------------------------------


async def _plan_request(
    client,  # noqa: ANN001
    project_id: int,
    model_id: int,
    *,
    kb_id: str,
) -> dict[str, Any]:
    resp = await client.post(
        f"/api/v1/projects/{project_id}/test-case-designs/plan",
        headers=ORIGIN,
        json={
            "modelId": model_id,
            "title": "订单超时关单测试设计",
            "requirementText": "订单支付超时后应自动关闭，并触发退款补偿。",
            "kbRefs": [{"kbId": kb_id, "entryCodes": ["BR-001", "BR-002"]}],
            "codePaths": ["src/order/close.py"],
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_tc311_stage1_plan_calls_gateway_and_persists_checkpoints(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "订单中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="order-domain",
        entries=[
            {"code": "BR-001", "title": "订单超时关闭规则", "summary": "超时关单"},
            {"code": "BR-002", "title": "退款补偿规则", "summary": "关单后退款"},
        ],
    )
    adapter = ScriptedAdapter([_checkpoints_payload()])
    app = make_app(settings, database, ai_gateway=AiGateway(adapter=adapter, retry_backoff=0))

    async with build_client(app) as client:
        await _login(client)
        builtin = (await client.get("/api/v1/skills")).json()["items"][0]
        assert builtin["slug"] == BUILTIN_TEST_CASE_SKILL_SLUG

        plan = await _plan_request(client, project_id, model_id, kb_id=kb_id)
        assert plan["status"] == "draft"
        assert plan["sessionId"] is not None
        assert plan["callId"] is not None
        assert plan["skillId"] == builtin["skillId"]
        assert plan["skillVersion"] == 1
        assert [cp["checkpointId"] for cp in plan["checkpoints"]] == ["CP-01", "CP-02"]
        assert plan["checkpoints"][0]["priority"] == "P0"
        assert plan["checkpoints"][0]["selected"] is True
        assert {link["code"] for link in plan["kbLinks"]} == {"BR-001", "BR-002"}
        assert all(len(link["contentDigest"]) == 64 for link in plan["kbLinks"])
        assert plan["codePaths"] == ["src/order/close.py"]

        detail = await client.get(f"/api/v1/test-case-designs/{plan['planId']}")
        assert detail.status_code == 200
        assert detail.json()["checkpoints"] == plan["checkpoints"]

        listed = await client.get(
            f"/api/v1/projects/{project_id}/test-case-designs"
        )
        assert listed.status_code == 200
        assert [item["planId"] for item in listed.json()["items"]] == [plan["planId"]]

    assert len(adapter.calls) == 1
    assert "阶段 1" in adapter.calls[0]["prepared"]
    assert "BR-001" in adapter.calls[0]["prepared"]

    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == 1
        assert (
            await db.scalar(
                select(func.count())
                .select_from(SessionEvent)
                .where(SessionEvent.type == "input_text")
            )
            == 1
        )
        session = await db.get(AnalysisSession, plan["sessionId"])
        assert session is not None
        assert session.entrance_key == "case-library"


@pytest.mark.asyncio
async def test_tc312_generate_rejects_empty_selection_without_calling_model(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "订单中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="order-domain",
        entries=[
            {"code": "BR-001", "title": "订单超时关闭规则", "summary": "超时关单"},
            {"code": "BR-002", "title": "退款补偿规则", "summary": "关单后退款"},
        ],
    )
    adapter = ScriptedAdapter([_checkpoints_payload()])
    app = make_app(settings, database, ai_gateway=AiGateway(adapter=adapter, retry_backoff=0))

    async with build_client(app) as client:
        await _login(client)
        plan = await _plan_request(client, project_id, model_id, kb_id=kb_id)

        empty = await client.post(
            f"/api/v1/test-case-designs/{plan['planId']}/generate",
            headers=ORIGIN,
            json={"selectedCheckpointIds": []},
        )
        assert empty.status_code == 400
        assert empty.json()["code"] == "no_checkpoints_selected"

        unknown = await client.post(
            f"/api/v1/test-case-designs/{plan['planId']}/generate",
            headers=ORIGIN,
            json={"selectedCheckpointIds": ["CP-404"]},
        )
        assert unknown.status_code == 400
        assert unknown.json()["code"] == "no_checkpoints_selected"

    assert len(adapter.calls) == 1  # 只有阶段 1 调用
    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(TestCase)) == 0


@pytest.mark.asyncio
async def test_tc313_stage2_generate_persists_cases_with_kb_links_and_digests(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "订单中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="order-domain",
        entries=[
            {"code": "BR-001", "title": "订单超时关闭规则", "summary": "超时关单"},
            {"code": "BR-002", "title": "退款补偿规则", "summary": "关单后退款"},
        ],
    )
    cases_payload = (
        '{"cases": ['
        '{"checkpointId": "CP-01", "caseCode": "TC-ORD-001", '
        '"module": "订单中心/超时关单", "title": "超时订单自动关闭", '
        '"priority": "P0", "caseType": "boundary", '
        '"preconditions": ["存在待支付订单"], '
        '"steps": [{"stepNo": 1, "action": "等待超时", "expected": "订单关闭"}], '
        '"expectedSummary": "订单状态变为 closed", '
        '"kbCodes": ["BR-001"], "codePaths": ["src/order/close.py"]},'
        '{"checkpointId": "CP-02", "title": "退款补偿幂等", '
        '"priority": "P9", "caseType": "weird", "steps": ["触发补偿"]}'
        "]}"
    )
    adapter = ScriptedAdapter([_checkpoints_payload(), cases_payload])
    app = make_app(settings, database, ai_gateway=AiGateway(adapter=adapter, retry_backoff=0))

    async with build_client(app) as client:
        await _login(client)
        plan = await _plan_request(client, project_id, model_id, kb_id=kb_id)

        generated = await client.post(
            f"/api/v1/test-case-designs/{plan['planId']}/generate",
            headers=ORIGIN,
            json={"selectedCheckpointIds": ["CP-01", "CP-02"]},
        )
        assert generated.status_code == 200, generated.text
        body = generated.json()
        assert body["planId"] == plan["planId"]
        assert body["sessionId"] == plan["sessionId"]
        assert body["generatedCount"] == 2

        first, second = body["items"]
        assert first["caseCode"] == "TC-ORD-001"
        assert first["priority"] == "P0"
        assert first["caseType"] == "boundary"
        assert [link["code"] for link in first["kbLinks"]] == ["BR-001"]
        assert len(first["kbLinks"][0]["contentDigest"]) == 64
        assert first["codePaths"] == ["src/order/close.py"]
        assert first["staleStatus"] == "fresh"
        assert first["checkpointId"] == "CP-01"

        assert second["priority"] == "P2"  # 非法 P9 回落到检查点优先级
        assert second["caseType"] == "security"
        assert [link["code"] for link in second["kbLinks"]] == ["BR-002"]
        assert second["steps"][0]["action"] == "触发补偿"

        detail = await client.get(f"/api/v1/test-case-designs/{plan['planId']}")
        assert detail.json()["status"] == "generated"

        listed = await client.get(f"/api/v1/projects/{project_id}/test-cases")
        assert listed.status_code == 200
        assert listed.json()["summary"]["totalCount"] == 2

    assert len(adapter.calls) == 2
    assert "阶段 2" in adapter.calls[1]["prepared"]
    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(TestCase)) == 2


# ---------------------------------------------------------------------------
# TC-314 ~ TC-317：Stale、CRUD 与导出
# ---------------------------------------------------------------------------


async def _stale_fixture(database) -> tuple[int, str, dict[str, str]]:  # noqa: ANN001
    project_id = await seed_project(database.sessionmaker, "订单中心")
    kb_id = await _seed_kb(
        database.sessionmaker,
        project_id,
        name="order-domain",
        entries=[
            {
                "code": "BR-001",
                "title": "订单超时关闭规则",
                "summary": "超时关单",
                "content_digest": "a" * 64,
            },
            {
                "code": "BR-002",
                "title": "退款补偿规则",
                "summary": "关单后退款",
                "content_digest": "b" * 64,
            },
            {
                "code": "BR-003",
                "title": "库存扣减规则",
                "summary": "下单扣减库存",
                "content_digest": "c" * 64,
            },
        ],
    )
    digests = {"BR-001": "a" * 64, "BR-002": "b" * 64, "BR-003": "c" * 64}
    return project_id, kb_id, digests


@pytest.mark.asyncio
async def test_tc314_list_test_cases_computes_dynamic_stale_reasons(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id, kb_id, digests = await _stale_fixture(database)

    fresh_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ST-001",
        module="订单中心/超时关单",
        title="正常用例",
        kb_links=[_anchor(kb_id, "order-domain", "BR-002", "退款补偿规则", digests["BR-002"])],
    )
    modified_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ST-002",
        module="订单中心/超时关单",
        title="规则变更后的用例",
        kb_links=[_anchor(kb_id, "order-domain", "BR-001", "订单超时关闭规则", digests["BR-001"])],
    )
    removed_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ST-003",
        module="订单中心/退款",
        title="条目移除后的用例",
        kb_links=[_anchor(kb_id, "order-domain", "BR-003", "库存扣减规则", digests["BR-003"])],
    )
    deleted_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ST-004",
        module="库存中心/盘点",
        title="知识库删除后的用例",
        priority="P0",
        kb_links=[_anchor("0" * 32, "ghost-kb", "BR-009", "已删除库规则", "d" * 64)],
    )

    async with database.sessionmaker() as db:
        entry = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb_id,
                KnowledgeEntry.code_key == "br-001",
            )
        )
        entry.content_digest = "e" * 64
        removed = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb_id,
                KnowledgeEntry.code_key == "br-003",
            )
        )
        await db.delete(removed)
        await db.commit()

    app = make_app(settings, database)
    async with build_client(app) as client:
        await _login(client)
        resp = await client.get(f"/api/v1/projects/{project_id}/test-cases")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        items = {item["caseId"]: item for item in body["items"]}

        assert body["summary"]["totalCount"] == 4
        assert body["summary"]["staleCount"] == 3
        assert body["summary"]["freshCount"] == 1
        assert body["summary"]["byPriority"] == {
            "P0": 1,
            "P1": 3,
            "P2": 0,
            "P3": 0,
        }
        assert body["summary"]["moduleTree"] == [
            {
                "name": "库存中心",
                "count": 1,
                "children": [{"name": "盘点", "count": 1, "children": []}],
            },
            {
                "name": "订单中心",
                "count": 3,
                "children": [
                    {"name": "超时关单", "count": 2, "children": []},
                    {"name": "退款", "count": 1, "children": []},
                ],
            },
        ]

        assert items[fresh_id]["staleStatus"] == "fresh"
        assert items[fresh_id]["staleReasons"] == []

        assert items[modified_id]["staleStatus"] == "stale"
        assert items[modified_id]["staleReasons"] == ["entry_modified"]
        assert items[modified_id]["staleDetails"][0]["reason"] == "entry_modified"
        assert items[modified_id]["staleDetails"][0]["code"] == "BR-001"

        assert items[removed_id]["staleReasons"] == ["entry_removed"]
        assert items[deleted_id]["staleReasons"] == ["kb_deleted"]

        stale_only = await client.get(
            f"/api/v1/projects/{project_id}/test-cases?staleOnly=true"
        )
        assert stale_only.status_code == 200
        assert stale_only.json()["summary"]["totalCount"] == 3

        filtered = await client.get(
            f"/api/v1/projects/{project_id}/test-cases?priority=P0"
        )
        assert [item["caseId"] for item in filtered.json()["items"]] == [deleted_id]

        searched = await client.get(
            f"/api/v1/projects/{project_id}/test-cases?q=知识库删除"
        )
        assert [item["caseId"] for item in searched.json()["items"]] == [deleted_id]

        by_module = await client.get(
            f"/api/v1/projects/{project_id}/test-cases?module=订单中心"
        )
        assert by_module.json()["summary"]["totalCount"] == 3


@pytest.mark.asyncio
async def test_tc315_acknowledge_stale_refreshes_links_and_clears_stale(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id, kb_id, digests = await _stale_fixture(database)
    case_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ACK-001",
        module="订单中心/超时关单",
        title="待复核用例",
        kb_links=[
            _anchor(kb_id, "order-domain", "BR-001", "订单超时关闭规则", digests["BR-001"]),
            _anchor(kb_id, "order-domain", "BR-002", "退款补偿规则", digests["BR-002"]),
            _anchor(kb_id, "order-domain", "BR-999", "已删除条目", "f" * 64),
        ],
    )
    removed_only_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-ACK-002",
        module="订单中心/退款",
        title="锚点已全部失效",
        kb_links=[_anchor("0" * 32, "ghost-kb", "BR-009", "旧规则", "d" * 64)],
    )

    async with database.sessionmaker() as db:
        entry = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb_id,
                KnowledgeEntry.code_key == "br-001",
            )
        )
        entry.content_digest = "9" * 64
        await db.commit()

    app = make_app(settings, database)
    async with build_client(app) as client:
        await _login(client)

        before = (await client.get(f"/api/v1/test-cases/{case_id}")).json()
        assert before["staleStatus"] == "stale"
        assert before["staleReasons"] == ["entry_modified", "entry_removed"]

        ack = await client.post(
            f"/api/v1/test-cases/{case_id}/acknowledge-stale", headers=ORIGIN
        )
        assert ack.status_code == 200, ack.text
        body = ack.json()
        assert body["staleStatus"] == "fresh"
        assert body["staleReasons"] == []
        assert [link["code"] for link in body["kbLinks"]] == ["BR-001", "BR-002"]
        assert body["kbLinks"][0]["contentDigest"] == "9" * 64
        assert body["kbLinks"][1]["contentDigest"] == digests["BR-002"]

        again = (await client.get(f"/api/v1/test-cases/{case_id}")).json()
        assert again["staleStatus"] == "fresh"

        empty_ack = await client.post(
            f"/api/v1/test-cases/{removed_only_id}/acknowledge-stale", headers=ORIGIN
        )
        assert empty_ack.status_code == 200
        assert empty_ack.json()["kbLinks"] == []
        assert empty_ack.json()["staleStatus"] == "fresh"


@pytest.mark.asyncio
async def test_tc316_patch_and_delete_test_case(settings, database) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "订单中心")
    case_id = await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-EDIT-001",
        module="订单中心/超时关单",
        title="待编辑用例",
        kb_links=[],
    )
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)
        patched = await client.patch(
            f"/api/v1/test-cases/{case_id}",
            headers=ORIGIN,
            json={
                "title": "已编辑用例",
                "priority": "P0",
                "steps": [{"stepNo": 1, "action": "新步骤", "expected": "新预期"}],
                "codePaths": ["src/order/close.py"],
            },
        )
        assert patched.status_code == 200, patched.text
        body = patched.json()
        assert body["title"] == "已编辑用例"
        assert body["priority"] == "P0"
        assert body["steps"] == [{"stepNo": 1, "action": "新步骤", "expected": "新预期"}]
        assert body["codePaths"] == ["src/order/close.py"]
        assert body["staleStatus"] == "fresh"

        invalid = await client.patch(
            f"/api/v1/test-cases/{case_id}",
            headers=ORIGIN,
            json={"priority": "PX"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["code"] == "validation_error"

        deleted = await client.delete(f"/api/v1/test-cases/{case_id}", headers=ORIGIN)
        assert deleted.status_code == 204

        missing = await client.get(f"/api/v1/test-cases/{case_id}")
        assert missing.status_code == 404
        assert missing.json()["code"] == "test_case_not_found"


@pytest.mark.asyncio
async def test_tc317_export_test_cases_in_csv_markdown_and_json(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id, kb_id, digests = await _stale_fixture(database)
    await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-EXP-001",
        module="订单中心/超时关单",
        title="超时订单自动关闭",
        kb_links=[
            _anchor(kb_id, "order-domain", "BR-002", "退款补偿规则", digests["BR-002"])
        ],
        code_paths=["src/order/close.py"],
    )
    await _seed_case(
        database.sessionmaker,
        project_id,
        case_code="TC-EXP-002",
        module="订单中心/超时关单",
        title="待复核导出用例",
        kb_links=[
            _anchor(kb_id, "order-domain", "BR-001", "订单超时关闭规则", digests["BR-001"])
        ],
        code_paths=["src/order/refund.py"],
    )
    async with database.sessionmaker() as db:
        entry = await db.scalar(
            select(KnowledgeEntry).where(
                KnowledgeEntry.kb_id == kb_id,
                KnowledgeEntry.code_key == "br-001",
            )
        )
        entry.content_digest = "8" * 64
        await db.commit()

    app = make_app(settings, database)
    async with build_client(app) as client:
        await _login(client)

        csv_resp = await client.get(
            f"/api/v1/projects/{project_id}/test-cases/export?format=csv"
        )
        assert csv_resp.status_code == 200
        assert csv_resp.headers["content-type"].startswith("text/csv")
        assert "caseCode" in csv_resp.text
        assert "TC-EXP-001" in csv_resp.text
        assert "BR-002" in csv_resp.text
        assert "src/order/close.py" in csv_resp.text
        assert "fresh" in csv_resp.text
        assert "stale" in csv_resp.text

        md_resp = await client.get(
            f"/api/v1/projects/{project_id}/test-cases/export?format=markdown"
        )
        assert md_resp.status_code == 200
        assert md_resp.headers["content-type"].startswith("text/markdown")
        assert "| 编号 |" in md_resp.text
        assert "TC-EXP-001" in md_resp.text
        assert "TC-EXP-002" in md_resp.text

        json_resp = await client.get(
            f"/api/v1/projects/{project_id}/test-cases/export?format=json"
        )
        assert json_resp.status_code == 200
        assert json_resp.headers["content-type"].startswith("application/json")
        exported = {item["caseCode"]: item for item in json_resp.json()["items"]}
        assert exported["TC-EXP-001"]["staleStatus"] == "fresh"
        assert exported["TC-EXP-002"]["staleStatus"] == "stale"
        assert exported["TC-EXP-002"]["staleReasons"] == ["entry_modified"]

        invalid = await client.get(
            f"/api/v1/projects/{project_id}/test-cases/export?format=xml"
        )
        assert invalid.status_code == 400
        assert invalid.json()["code"] == "validation_error"


# ---------------------------------------------------------------------------
# TC-318：用例库入口点亮为 live
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tc318_case_library_entrance_is_live(settings, database) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)

        listed = await client.get("/api/v1/entrances")
        assert listed.status_code == 200
        by_key = {item["key"]: item for item in listed.json()["items"]}
        assert by_key["case-library"]["status"] == "live"
        assert [item["key"] for item in listed.json()["items"] if item["status"] == "live"] == [
            "case-library"
        ]

        detail = await client.get("/api/v1/entrances/case-library")
        assert detail.status_code == 200
        assert detail.json()["status"] == "live"
