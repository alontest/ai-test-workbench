"""会话接口：创建、筛选、时间线、完成与删除。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
    seed_session,
)
from workbench.db.models import AnalysisSession, KnowledgeBase

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
KB_ID = "3f2504e04f8911d39a0c0305e82c3301"


@pytest.fixture
async def client(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as http:
        login = await http.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        http.app = app
        yield http


async def _project(client) -> int:  # noqa: ANN001
    body = (
        await client.post(
            "/api/v1/projects", json={"name": "支付中心"}, headers=ORIGIN
        )
    ).json()
    return body["projectId"]


async def _model(client) -> int:  # noqa: ANN001
    provider = (
        await client.post(
            "/api/v1/providers",
            json={
                "name": "OpenAI",
                "protocol": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "apiKey": "sk-test-qwerty",
            },
            headers=ORIGIN,
        )
    ).json()
    model = (
        await client.post(
            f"/api/v1/providers/{provider['providerId']}/models",
            json={"modelName": "gpt-4.1", "displayName": "GPT-4.1"},
            headers=ORIGIN,
        )
    ).json()
    return model["modelId"]


@pytest.mark.asyncio
async def test_tc026_api_create_session(client) -> None:
    project_id = await _project(client)
    model_id = await _model(client)

    response = await client.post(
        "/api/v1/sessions",
        json={
            "projectId": project_id,
            "entranceKey": "case-library",
            "title": "排查一次失败",
            "modelId": model_id,
        },
        headers=ORIGIN,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["sessionId"] > 0
    assert body["project"]["name"] == "支付中心"
    assert body["model"]["displayName"] == "GPT-4.1"

    listing = await client.get("/api/v1/sessions")
    assert listing.json()["items"][0]["sessionId"] == body["sessionId"]

    bad_title = await client.post(
        "/api/v1/sessions",
        json={
            "projectId": project_id,
            "entranceKey": "case-library",
            "title": "x" * 201,
            "modelId": model_id,
        },
        headers=ORIGIN,
    )
    assert bad_title.status_code == 400

    bad_entrance = await client.post(
        "/api/v1/sessions",
        json={
            "projectId": project_id,
            "entranceKey": "unknown",
            "title": "x",
            "modelId": model_id,
        },
        headers=ORIGIN,
    )
    assert bad_entrance.status_code == 400


@pytest.mark.asyncio
async def test_tc015_session_requires_project(client, database) -> None:
    model_id = await _model(client)
    response = await client.post(
        "/api/v1/sessions",
        json={
            "projectId": 999999,
            "entranceKey": "case-library",
            "title": "x",
            "modelId": model_id,
        },
        headers=ORIGIN,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "project_not_found"
    assert response.json()["details"][0]["field"] == "projectId"
    async with database.sessionmaker() as db:
        assert (
            await db.scalar(select(func.count()).select_from(AnalysisSession)) == 0
        )


@pytest.mark.asyncio
async def test_tc027_api_filters(client, database) -> None:
    project_a = await seed_project(database.sessionmaker, name="项目A")
    project_b = await seed_project(database.sessionmaker, name="项目B")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    a1 = await seed_session(database.sessionmaker, project_id=project_a, model_id=model_id, title="a1")
    a2 = await seed_session(database.sessionmaker, project_id=project_a, model_id=model_id, title="a2")
    b1 = await seed_session(database.sessionmaker, project_id=project_b, model_id=model_id, title="b1")

    filtered = await client.get(f"/api/v1/sessions?projectId={project_a}")
    assert {item["sessionId"] for item in filtered.json()["items"]} == {a1, a2}

    first = await client.get("/api/v1/sessions?limit=2")
    payload = first.json()
    assert len(payload["items"]) == 2
    assert payload["nextCursor"]
    second = await client.get(
        f"/api/v1/sessions?limit=2&cursor={payload['nextCursor']}"
    )
    ids = {item["sessionId"] for item in payload["items"]}
    ids |= {item["sessionId"] for item in second.json()["items"]}
    assert ids == {a1, a2, b1}

    bad_status = await client.get("/api/v1/sessions?status=unknown")
    assert bad_status.status_code == 400
    bad_limit = await client.get("/api/v1/sessions?limit=101")
    assert bad_limit.status_code == 400

    none = await client.get("/api/v1/sessions?status=failed")
    assert none.json() == {"items": [], "nextCursor": None}


@pytest.mark.asyncio
async def test_tc028_api_events_order(client, database) -> None:
    from workbench.services import sessions

    project_id = await seed_project(database.sessionmaker)
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    session_id = await seed_session(
        database.sessionmaker, project_id=project_id, model_id=model_id
    )
    await sessions.append_event(
        session_id, "input_text", {"title": "t", "text": "boom", "charCount": 4}
    )
    await sessions.append_event(
        session_id,
        "artifact",
        {
            "artifactId": 1,
            "fileName": "a.log",
            "byteSize": 3,
            "mimeType": "text/plain",
            "kind": "upload",
        },
    )
    await sessions.append_event(
        session_id,
        "status_change",
        {
            "from": "in_progress",
            "to": "completed",
            "actor": "local-user",
            "at": "2026-11-18T00:00:00Z",
        },
    )

    page = await client.get(f"/api/v1/sessions/{session_id}/events?limit=2")
    payload = page.json()
    assert [item["type"] for item in payload["items"]] == ["input_text", "artifact"]
    assert payload["nextCursor"]
    rest = await client.get(
        f"/api/v1/sessions/{session_id}/events?limit=2&cursor={payload['nextCursor']}"
    )
    assert [item["type"] for item in rest.json()["items"]] == ["status_change"]

    too_big = await client.get(f"/api/v1/sessions/{session_id}/events?limit=201")
    assert too_big.status_code == 400

    missing = await client.get("/api/v1/sessions/999999/events")
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_tc029_api_complete_idempotent(client, database) -> None:
    project_id = await seed_project(database.sessionmaker)
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    session_id = await seed_session(
        database.sessionmaker, project_id=project_id, model_id=model_id
    )

    done = await client.post(f"/api/v1/sessions/{session_id}/complete", headers=ORIGIN)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert done.json()["closedAt"]

    again = await client.post(
        f"/api/v1/sessions/{session_id}/complete", headers=ORIGIN
    )
    assert again.status_code == 409
    assert again.json()["code"] == "session_closed"

    text = await client.post(
        f"/api/v1/sessions/{session_id}/inputs/text",
        json={"title": "t", "text": "boom"},
        headers=ORIGIN,
    )
    assert text.status_code == 409
    assert text.json()["code"] == "session_closed"


@pytest.mark.asyncio
async def test_tc030_api_delete(client, database) -> None:
    project_id, model_id, session_id = await _seed_graph(database.sessionmaker)
    other = await seed_session(
        database.sessionmaker, project_id=project_id, model_id=model_id, title="保留"
    )

    response = await client.delete(f"/api/v1/sessions/{session_id}", headers=ORIGIN)
    assert response.status_code == 204
    assert response.text == ""

    gone = await client.get(f"/api/v1/sessions/{session_id}")
    assert gone.status_code == 404

    still = await client.get(f"/api/v1/sessions/{other}")
    assert still.status_code == 200

    again = await client.delete(f"/api/v1/sessions/{session_id}", headers=ORIGIN)
    assert again.status_code == 404


async def _seed_graph(sessionmaker) -> tuple[int, int, int]:  # noqa: ANN001
    from helpers import seed_session_graph

    return await seed_session_graph(sessionmaker)


@pytest.mark.asyncio
async def test_tc031_recent_sessions_limit10(client, database) -> None:
    project_id = await seed_project(database.sessionmaker)
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)
    ids = []
    for index in range(11):
        ids.append(
            await seed_session(
                database.sessionmaker,
                project_id=project_id,
                model_id=model_id,
                title=f"会话 {index}",
            )
        )

    response = await client.get("/api/v1/sessions?limit=10")
    payload = response.json()
    assert len(payload["items"]) == 10
    assert payload["nextCursor"] is not None
    assert [item["sessionId"] for item in payload["items"]] == sorted(
        ids, reverse=True
    )[:10]

    for session_id in ids:
        await client.delete(f"/api/v1/sessions/{session_id}", headers=ORIGIN)
    empty = await client.get("/api/v1/sessions?limit=10")
    assert empty.json() == {"items": [], "nextCursor": None}


@pytest.mark.asyncio
async def test_tc070_knowledge_injection_timeline_payload(client, database) -> None:
    import hashlib

    from sqlalchemy import text

    from workbench.core.redaction import redact
    from workbench.db.base import utcnow
    from workbench.db.models import AiCallRecord, ModelBinding, SessionEvent
    from workbench.services import sessions as sessions_service

    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    session_id = await seed_session(sm, project_id=project_id, model_id=model_id)
    items = [
        {
            "kbId": KB_ID,
            "kbName": "支付中心知识库",
            "kbVersion": 2,
            "entryCodes": ["ENT-012", "BR-003"],
            "injectedChars": 3,
        }
    ]
    snapshot = {
        "items": items,
        "promptChars": 5,
        "injectedChars": 3,
        "totalChars": 8,
        "excludedCodes": ["ENT-009"],
    }
    async with sm() as db:
        model = await db.get(ModelBinding, model_id)
        assert model is not None
        now = utcnow()
        record = AiCallRecord(
            session_id=session_id,
            model_id=model_id,
            provider_id=model.provider_id,
            model_name_snapshot=model.model_name,
            display_name_snapshot=model.display_name,
            provider_name_snapshot="OpenAI",
            protocol_snapshot="openai_compatible",
            status="success",
            prompt_digest=hashlib.sha256(b"prompt").hexdigest(),
            prompt_preview=redact("prompt", max_length=200),
            prompt_char_count=8,
            knowledge_injection=items,
            injected_chars=3,
            prompt_chars=5,
            total_chars=8,
            result_text="ok",
            created_at=now,
            finished_at=now,
            latency_ms=12,
        )
        db.add(record)
        await db.flush()
        db.add(
            SessionEvent(
                session_id=session_id,
                type="knowledge_injection",
                payload=snapshot,
                created_at=now,
            )
        )
        await db.commit()
        call_id = record.call_id

    events = await client.get(f"/api/v1/sessions/{session_id}/events")
    assert events.status_code == 200
    injection_event = next(
        item for item in events.json()["items"] if item["type"] == "knowledge_injection"
    )
    payload = injection_event["payload"]
    assert payload["promptChars"] == 5
    assert payload["injectedChars"] == 3
    assert payload["totalChars"] == 8
    assert payload["excludedCodes"] == ["ENT-009"]
    assert payload["items"][0]["kbId"] == KB_ID
    assert payload["items"][0]["kbDeleted"] is True
    assert "body" not in payload
    assert "text" not in payload
    assert "body" not in payload["items"][0]

    detail = await client.get(f"/api/v1/calls/{call_id}")
    assert detail.json()["knowledgeInjection"][0]["kbDeleted"] is True
    assert detail.json()["knowledgeInjection"][0]["kbName"] == "支付中心知识库"

    async with sm() as db:
        # knowledge_base 由迁移 0007 创建；这里只验证「行存在 / 不存在」。
        db.add(
            KnowledgeBase(
                kb_id=KB_ID,
                project_id=project_id,
                name="支付中心知识库",
                name_key="支付中心知识库",
                version=2,
                current_flag="1",
                status="ready",
                source_index_sha256="0" * 64,
                storage_dir=f"knowledge-bases/{KB_ID}",
            )
        )
        await db.commit()

    present_events = await client.get(f"/api/v1/sessions/{session_id}/events")
    present_payload = next(
        item
        for item in present_events.json()["items"]
        if item["type"] == "knowledge_injection"
    )["payload"]
    assert present_payload["items"][0]["kbDeleted"] is False
    present_detail = await client.get(f"/api/v1/calls/{call_id}")
    assert present_detail.json()["knowledgeInjection"][0]["kbDeleted"] is False

    async with sm() as db:
        await db.execute(
            text("DELETE FROM knowledge_base WHERE kb_id = :kb_id"),
            {"kb_id": KB_ID},
        )
        await db.commit()
    deleted_events = await client.get(f"/api/v1/sessions/{session_id}/events")
    deleted_payload = next(
        item
        for item in deleted_events.json()["items"]
        if item["type"] == "knowledge_injection"
    )["payload"]
    assert deleted_payload["items"][0]["kbDeleted"] is True
    assert deleted_payload["items"][0]["kbName"] == "支付中心知识库"

    async with sm() as db:
        await db.execute(text("DROP TABLE knowledge_base"))
        await db.commit()
    dropped = await client.get(f"/api/v1/sessions/{session_id}/events")
    dropped_payload = next(
        item for item in dropped.json()["items"] if item["type"] == "knowledge_injection"
    )["payload"]
    assert dropped_payload["items"][0]["kbDeleted"] is True

    # 无注入事件不得被误标
    await sessions_service.append_event(
        session_id, "input_text", {"title": "t", "text": "boom", "charCount": 4}
    )
    mixed = await client.get(f"/api/v1/sessions/{session_id}/events")
    input_event = next(item for item in mixed.json()["items"] if item["type"] == "input_text")
    assert "kbDeleted" not in input_event["payload"]
