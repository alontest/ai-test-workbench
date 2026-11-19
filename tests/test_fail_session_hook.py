"""未捕获异常标记会话失败。用例名带 TC 编号。"""

from __future__ import annotations

import pytest
from fastapi import Request
from sqlalchemy import select

from helpers import build_client, make_app, seed_admin, seed_session_graph
from workbench.db.models import AnalysisSession, SessionEvent

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


@pytest.mark.asyncio
async def test_tc029_unhandled_error_marks_failed(settings, database) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)

    @app.get("/api/v1/_boom_session")
    async def boom(request: Request):  # noqa: ANN202
        raw = request.query_params.get("sessionId")
        request.state.session_id = int(raw) if raw else None
        raise RuntimeError("boom")

    @app.get("/api/v1/_nice_error")
    async def nice(request: Request):  # noqa: ANN202
        request.state.session_id = request.query_params.get("sessionId")
        from workbench.api.errors import ApiError

        raise ApiError(409, "session_closed", "会话已结束。")

    async with build_client(app) as client:
        await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        project_id, model_id, session_id = await seed_session_graph(
            database.sessionmaker
        )

        response = await client.get(
            f"/api/v1/_boom_session?sessionId={session_id}"
        )
        assert response.status_code == 500
        assert response.json()["code"] == "internal_error"

        async with database.sessionmaker() as db:
            session = await db.get(AnalysisSession, session_id)
            assert session.status == "failed"
            assert session.closed_at is not None
            events = list(await db.scalars(select(SessionEvent)))
        assert events[-1].type == "status_change"
        assert events[-1].payload["actor"] == "system"
        assert events[-1].payload["reason"] == "unhandled error"

        other = await seed_session_graph_other(database.sessionmaker)
        business = await client.get(f"/api/v1/_nice_error?sessionId={other}")
        assert business.status_code == 409
        async with database.sessionmaker() as db:
            assert (await db.get(AnalysisSession, other)).status == "in_progress"

        # 无会话上下文的 500 不改任何状态。
        no_scope = await client.get("/api/v1/_boom_session")
        assert no_scope.status_code == 500
        async with database.sessionmaker() as db:
            assert (await db.get(AnalysisSession, other)).status == "in_progress"


async def seed_session_graph_other(sessionmaker) -> int:  # noqa: ANN001
    from helpers import seed_model, seed_project, seed_provider, seed_session

    project_id = await seed_project(sessionmaker, name="另一个项目")
    provider_id = await seed_provider(sessionmaker, name="Other")
    model_id = await seed_model(sessionmaker, provider_id, model_name="other-model")
    return await seed_session(sessionmaker, project_id=project_id, model_id=model_id)
