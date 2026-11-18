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
from workbench.db.models import AnalysisSession

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


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
