"""批次 B 最小闭环冒烟：登录 → 项目 → 提供商/模型 → 会话 → 文本 → 调用。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin
from workbench.db.models import AiCallRecord, AnalysisSession

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


class FakeAI:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return "fixed answer"

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_tc062_batch_b_minimal_loop(settings, database) -> None:
    from workbench.services.ai_gateway import AiGateway

    await seed_admin(database.sessionmaker, ADMIN)
    fake = FakeAI()
    app = make_app(settings, database, ai_gateway=AiGateway(adapter=fake, retry_backoff=0))

    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        assert "aw_session" in client.cookies

        project = await client.post(
            "/api/v1/projects",
            json={"name": "支付中心", "repoUrl": "https://example.com/pay"},
            headers=ORIGIN,
        )
        assert project.status_code == 201

        provider = await client.post(
            "/api/v1/providers",
            json={
                "name": "OpenAI",
                "protocol": "openai_compatible",
                "baseUrl": "https://api.example.com/v1",
                "apiKey": "sk-test-qwerty",
            },
            headers=ORIGIN,
        )
        assert provider.status_code == 201
        assert "apiKey" not in provider.json()

        model = await client.post(
            f"/api/v1/providers/{provider.json()['providerId']}/models",
            json={"modelName": "gpt-4.1", "displayName": "GPT-4.1"},
            headers=ORIGIN,
        )
        assert model.status_code == 201

        session = await client.post(
            "/api/v1/sessions",
            json={
                "projectId": project.json()["projectId"],
                "entranceKey": "case-library",
                "title": "冒烟",
                "modelId": model.json()["modelId"],
            },
            headers=ORIGIN,
        )
        assert session.status_code == 201
        session_id = session.json()["sessionId"]
        before = session.json()["updatedAt"]

        text = await client.post(
            f"/api/v1/sessions/{session_id}/inputs/text",
            json={"title": "日志", "text": "boom"},
            headers=ORIGIN,
        )
        assert text.status_code == 201

        call = await client.post(
            f"/api/v1/sessions/{session_id}/ai/complete",
            json={"prompt": "boom"},
            headers=ORIGIN,
        )
        assert call.status_code == 200
        assert call.json()["resultText"] == "fixed answer"

        events = await client.get(f"/api/v1/sessions/{session_id}/events")
        types = [item["type"] for item in events.json()["items"]]
        assert "input_text" in types and "call" in types

        detail = await client.get(f"/api/v1/sessions/{session_id}")
        assert detail.json()["updatedAt"] > before

        async with database.sessionmaker() as db:
            records = await db.scalar(
                select(func.count()).select_from(AiCallRecord)
            )
            assert records == 1
            record = (await db.scalars(select(AiCallRecord))).one()
            assert record.status == "success"
            assert (await db.get(AnalysisSession, session_id)).status == "in_progress"

        assert len(fake.calls) == 1
