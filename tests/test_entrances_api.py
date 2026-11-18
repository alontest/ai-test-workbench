"""入口配置 API、SPA fallback 与占位页无副作用。用例名带 TC 编号。"""

from __future__ import annotations

from dataclasses import replace

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
from workbench.core.entrances import ENTRANCES, Entrance
from workbench.db.models import AiCallRecord, AnalysisSession, SessionEvent

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
EXPECTED_KEYS = (
    "case-library",
    "bug-analysis",
    "log-triage",
    "sql-analysis",
    "regression-list",
    "test-report",
)


@pytest.fixture
async def client(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as http:
        login = await http.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        yield http


def _with_dist(tmp_path, monkeypatch):  # noqa: ANN001, ANN202
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        "<!doctype html><title>workbench</title>", encoding="utf-8"
    )
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('ok')", encoding="utf-8")
    monkeypatch.setattr("workbench.main.WEB_DIST", dist)
    return dist


@pytest.mark.asyncio
async def test_tc051_api_entrances_six(client) -> None:
    response = await client.get("/api/v1/entrances")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["key"] for item in items] == list(EXPECTED_KEYS)
    assert len(items) == 6
    for item in items:
        assert item["name"]
        assert item["description"]
        assert item["domain"]
        assert item["status"] == "planned"
        assert "生成测试用例" not in item["name"]
        assert "生成测试用例" not in item["description"]
    keys = [item["key"] for item in items]
    assert len(keys) == len(set(keys))


@pytest.mark.asyncio
async def test_tc031_home_recent_sessions(client, database) -> None:
    sm = database.sessionmaker
    project_id = await seed_project(sm)
    provider_id = await seed_provider(sm)
    model_id = await seed_model(sm, provider_id)
    ids = []
    for index in range(11):
        ids.append(
            await seed_session(
                sm, project_id=project_id, model_id=model_id, title=f"会话 {index}"
            )
        )

    response = await client.get("/api/v1/sessions?limit=10")
    payload = response.json()
    assert len(payload["items"]) == 10
    assert payload["nextCursor"] is not None
    assert [item["sessionId"] for item in payload["items"]] == sorted(ids, reverse=True)[
        :10
    ]

    for session_id in ids:
        deleted = await client.delete(f"/api/v1/sessions/{session_id}", headers=ORIGIN)
        assert deleted.status_code == 204
    empty = await client.get("/api/v1/sessions?limit=10")
    assert empty.json() == {"items": [], "nextCursor": None}


@pytest.mark.asyncio
async def test_tc052_spa_fallback_entrance_route(
    settings, database, tmp_path, monkeypatch
) -> None:
    _with_dist(tmp_path, monkeypatch)
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)

    async with build_client(app) as anonymous:
        unauth = await anonymous.get("/entrances/bug-analysis", follow_redirects=False)
        assert unauth.status_code == 302
        assert unauth.headers["location"] == "/login?next=%2Fentrances%2Fbug-analysis"

        missing_asset = await anonymous.get("/assets/missing.js")
        assert missing_asset.status_code == 404
        assert "workbench" not in missing_asset.text

    async with build_client(app) as http:
        login = await http.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        page = await http.get("/entrances/bug-analysis")
        assert page.status_code == 200
        assert "workbench" in page.text
        assert page.headers["content-type"].startswith("text/html")

        asset = await http.get("/assets/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text

        still_missing = await http.get("/assets/nope.js")
        assert still_missing.status_code == 404
        assert "workbench" not in still_missing.text


@pytest.mark.asyncio
async def test_tc053_unknown_entrance_rejected(client, database) -> None:
    async with database.sessionmaker() as db:
        before_sessions = await db.scalar(select(func.count()).select_from(AnalysisSession))
        before_events = await db.scalar(select(func.count()).select_from(SessionEvent))
        before_calls = await db.scalar(select(func.count()).select_from(AiCallRecord))

    for path in (
        "/entrances/unknown",
        "/entrances/Case-Library",
        "/api/v1/entrances/unknown",
        "/api/v1/entrances/Case-Library",
    ):
        response = await client.get(path)
        assert response.status_code == 400, path
        assert response.json()["code"] == "entrance_unknown"

    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(AnalysisSession)) == before_sessions
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == before_events
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == before_calls


@pytest.mark.asyncio
async def test_tc054_placeholder_metadata(client) -> None:
    listed = await client.get("/api/v1/entrances")
    assert listed.status_code == 200
    for item in listed.json()["items"]:
        detail = await client.get(f"/api/v1/entrances/{item['key']}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["key"] == item["key"]
        assert body["name"] == item["name"]
        assert body["domain"]
        assert body["status"] == "planned"
        assert body["description"]


@pytest.mark.asyncio
async def test_tc055_placeholder_has_no_side_effects(
    settings, database, tmp_path, monkeypatch
) -> None:
    _with_dist(tmp_path, monkeypatch)
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)

    async with database.sessionmaker() as db:
        before_sessions = await db.scalar(select(func.count()).select_from(AnalysisSession))
        before_events = await db.scalar(select(func.count()).select_from(SessionEvent))
        before_calls = await db.scalar(select(func.count()).select_from(AiCallRecord))

    async with build_client(app) as anonymous:
        unauth = await anonymous.get("/entrances/log-triage", follow_redirects=False)
        assert unauth.status_code == 302

    async with build_client(app) as http:
        await http.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        for _ in range(3):
            page = await http.get("/entrances/log-triage")
            assert page.status_code == 200

    async with database.sessionmaker() as db:
        assert await db.scalar(select(func.count()).select_from(AnalysisSession)) == before_sessions
        assert await db.scalar(select(func.count()).select_from(SessionEvent)) == before_events
        assert await db.scalar(select(func.count()).select_from(AiCallRecord)) == before_calls


@pytest.mark.asyncio
async def test_tc056_entrance_status_switch(client, monkeypatch) -> None:
    live = replace(ENTRANCES[1], status="live")
    patched = tuple(live if item.key == "bug-analysis" else item for item in ENTRANCES)
    monkeypatch.setattr("workbench.core.entrances.ENTRANCES", patched)

    listed = await client.get("/api/v1/entrances")
    by_key = {item["key"]: item for item in listed.json()["items"]}
    assert by_key["bug-analysis"]["status"] == "live"
    assert by_key["case-library"]["status"] == "planned"

    detail = await client.get("/api/v1/entrances/bug-analysis")
    assert detail.json()["status"] == "live"

    illegal = Entrance(
        key="bug-analysis",
        name="分析 bug",
        description="x",
        domain="diagnosis",
        status="beta",  # type: ignore[arg-type]
    )
    monkeypatch.setattr("workbench.core.entrances.ENTRANCES", (illegal,))
    with pytest.raises((ValueError, RuntimeError)):
        from workbench.core.entrances import iter_entrances

        iter_entrances()
