"""文本输入接口。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_session_graph
from vigil_workbench.db.models import AnalysisSession, SessionEvent

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


@pytest.fixture
async def ctx(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as client:
        await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        project_id, model_id, session_id = await seed_session_graph(database.sessionmaker)
        yield client, database, project_id, model_id, session_id


async def _event_count(sm) -> int:  # noqa: ANN001
    async with sm() as db:
        return await db.scalar(select(func.count()).select_from(SessionEvent))


@pytest.mark.asyncio
async def test_tc032_append_text_event(ctx) -> None:
    client, database, project_id, model_id, session_id = ctx
    response = await client.post(
        f"/api/v1/sessions/{session_id}/inputs/text",
        json={"title": "报错日志", "text": "boom trace"},
        headers=ORIGIN,
    )
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"eventId", "sessionId", "type", "payload", "createdAt"}
    assert body["type"] == "input_text"
    assert body["payload"] == {
        "title": "报错日志",
        "text": "boom trace",
        "charCount": 10,
    }

    events = await client.get(f"/api/v1/sessions/{session_id}/events")
    assert events.json()["items"][0]["eventId"] == body["eventId"]

    missing = await client.post(
        "/api/v1/sessions/999999/inputs/text",
        json={"title": "t", "text": "x"},
        headers=ORIGIN,
    )
    assert missing.status_code == 404
    assert missing.json()["code"] == "session_not_found"


@pytest.mark.asyncio
async def test_tc033_empty_text_rejected(ctx) -> None:
    client, database, project_id, model_id, session_id = ctx
    before = await _event_count(database.sessionmaker)
    for text in ("", "   ", "\n\t"):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/inputs/text",
            json={"title": "t", "text": text},
            headers=ORIGIN,
        )
        assert response.status_code == 400
        assert response.json()["code"] == "text_empty"
        assert response.json()["details"][0]["field"] == "text"

    for title in ("", "x" * 201):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/inputs/text",
            json={"title": title, "text": "body"},
            headers=ORIGIN,
        )
        assert response.status_code == 400
        assert response.json()["details"][0]["field"] == "title"

    assert await _event_count(database.sessionmaker) == before


@pytest.mark.asyncio
async def test_tc034_text_over_limit_rejected(ctx) -> None:
    client, database, project_id, model_id, session_id = ctx
    limit = "x" * 200_000
    ok = await client.post(
        f"/api/v1/sessions/{session_id}/inputs/text",
        json={"title": "t", "text": limit},
        headers=ORIGIN,
    )
    assert ok.status_code == 201
    assert ok.json()["payload"]["charCount"] == 200_000
    assert len(ok.json()["payload"]["text"]) == 200_000

    before = await _event_count(database.sessionmaker)
    too_long = await client.post(
        f"/api/v1/sessions/{session_id}/inputs/text",
        json={"title": "t", "text": "y" * 200_001},
        headers=ORIGIN,
    )
    assert too_long.status_code == 400
    body = too_long.json()
    assert body["code"] == "text_too_long"
    details = body["details"][0]
    assert details["charCount"] == 200_001
    assert details["maxChars"] == 200_000
    assert await _event_count(database.sessionmaker) == before


@pytest.mark.asyncio
async def test_tc035_updated_at_bumped(ctx) -> None:
    client, database, project_id, model_id, session_id = ctx

    async with database.sessionmaker() as db:
        before = (await db.get(AnalysisSession, session_id)).updated_at

    await client.post(
        f"/api/v1/sessions/{session_id}/inputs/text",
        json={"title": "t", "text": "boom"},
        headers=ORIGIN,
    )

    async with database.sessionmaker() as db:
        after = (await db.get(AnalysisSession, session_id)).updated_at
    assert after > before

    listing = await client.get("/api/v1/sessions")
    assert listing.json()["items"][0]["sessionId"] == session_id
