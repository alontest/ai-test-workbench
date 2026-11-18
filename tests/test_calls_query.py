"""调用记录查询：筛选、排序、详情与空态。用例名带 TC 编号。"""

from __future__ import annotations

import hashlib
from datetime import datetime

import pytest

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
    seed_session,
)
from workbench.core.redaction import redact
from workbench.db.models import AiCallRecord, ModelBinding

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
SECRET_PROMPT = "please inspect sk-abcdef1234 now"


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


async def _graph(sessionmaker, *, project_name: str = "支付中心", title: str = "排查"):
    project_id = await seed_project(sessionmaker, project_name)
    provider_id = await seed_provider(sessionmaker, name=f"P-{project_name}")
    model_id = await seed_model(
        sessionmaker, provider_id, model_name=f"m-{project_name}", display_name="GPT-4.1"
    )
    session_id = await seed_session(
        sessionmaker, project_id=project_id, model_id=model_id, title=title
    )
    return project_id, provider_id, model_id, session_id


async def _seed_call(
    sessionmaker,
    *,
    session_id: int,
    model_id: int,
    status: str,
    created_at: datetime,
    result_text: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    retry_count: int = 0,
    prompt: str = "hello",
    latency_ms: int = 120,
) -> int:
    async with sessionmaker() as db:
        model = await db.get(ModelBinding, model_id)
        assert model is not None
        row = AiCallRecord(
            session_id=session_id,
            model_id=model_id,
            provider_id=model.provider_id,
            model_name_snapshot=model.model_name,
            display_name_snapshot=model.display_name,
            provider_name_snapshot="OpenAI",
            protocol_snapshot="openai_compatible",
            status=status,
            prompt_digest=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            prompt_preview=redact(prompt, max_length=200),
            prompt_char_count=len(prompt),
            result_text=result_text,
            retry_count=retry_count,
            error_code=error_code,
            error_message=error_message,
            created_at=created_at,
            finished_at=created_at,
            latency_ms=latency_ms,
        )
        db.add(row)
        await db.commit()
        return row.call_id


@pytest.mark.asyncio
async def test_tc046_query_calls_ordering(client, database) -> None:
    sm = database.sessionmaker
    project_a, _provider_a, model_a, session_a = await _graph(sm, project_name="项目A")
    project_b, _provider_b, model_b, session_b = await _graph(
        sm, project_name="项目B", title="另一会话"
    )

    t0 = datetime(2026, 11, 10, 10, 0, 0)
    t1 = datetime(2026, 11, 10, 11, 0, 0)
    t2 = datetime(2026, 11, 10, 12, 0, 0)

    call_old = await _seed_call(
        sm,
        session_id=session_a,
        model_id=model_a,
        status="success",
        created_at=t0,
        result_text="旧成功结果，含 sk-should-not-leak",
        prompt=SECRET_PROMPT,
    )
    call_failed = await _seed_call(
        sm,
        session_id=session_a,
        model_id=model_a,
        status="failed",
        created_at=t1,
        error_code="auth",
        error_message="upstream 401 for sk-abcdef1234",
        retry_count=0,
        prompt=SECRET_PROMPT,
    )
    call_same_time_low = await _seed_call(
        sm,
        session_id=session_b,
        model_id=model_b,
        status="timeout",
        created_at=t2,
        error_code="timeout",
        error_message="upstream request timed out",
        retry_count=0,
    )
    call_same_time_high = await _seed_call(
        sm,
        session_id=session_a,
        model_id=model_a,
        status="success",
        created_at=t2,
        result_text="新成功",
    )

    listed = await client.get("/api/v1/calls")
    assert listed.status_code == 200
    body = listed.json()
    ids = [item["callId"] for item in body["items"]]
    assert ids == [call_same_time_high, call_same_time_low, call_failed, call_old]
    for item in body["items"]:
        assert "resultText" not in item
        blob = str(item)
        assert "sk-abcdef1234" not in blob
        assert "sk-should-not-leak" not in blob

    by_session = await client.get(f"/api/v1/calls?sessionId={session_a}")
    assert [item["callId"] for item in by_session.json()["items"]] == [
        call_same_time_high,
        call_failed,
        call_old,
    ]

    by_project = await client.get(f"/api/v1/calls?projectId={project_b}")
    assert [item["callId"] for item in by_project.json()["items"]] == [call_same_time_low]

    by_status = await client.get("/api/v1/calls?status=failed")
    assert [item["callId"] for item in by_status.json()["items"]] == [call_failed]

    by_time = await client.get(
        "/api/v1/calls?from=2026-11-10T10:30:00Z&to=2026-11-10T11:30:00Z"
    )
    assert [item["callId"] for item in by_time.json()["items"]] == [call_failed]

    page1 = await client.get("/api/v1/calls?limit=2")
    payload = page1.json()
    assert [item["callId"] for item in payload["items"]] == [
        call_same_time_high,
        call_same_time_low,
    ]
    assert payload["nextCursor"]
    page2 = await client.get(f"/api/v1/calls?limit=2&cursor={payload['nextCursor']}")
    rest = page2.json()
    assert [item["callId"] for item in rest["items"]] == [call_failed, call_old]
    assert set(payload["items"][0]) | set(rest["items"][0])
    assert {item["callId"] for item in payload["items"]}.isdisjoint(
        {item["callId"] for item in rest["items"]}
    )

    bad_time = await client.get("/api/v1/calls?from=not-a-date")
    assert bad_time.status_code == 400
    assert bad_time.json()["code"] == "validation_error"

    future = await client.get("/api/v1/calls?from=2099-01-01T00:00:00Z")
    assert future.status_code == 200
    assert future.json() == {"items": [], "nextCursor": None}


@pytest.mark.asyncio
async def test_tc047_failed_call_detail(client, database) -> None:
    sm = database.sessionmaker
    _project_id, _provider_id, model_id, session_id = await _graph(sm)
    failed_id = await _seed_call(
        sm,
        session_id=session_id,
        model_id=model_id,
        status="failed",
        created_at=datetime(2026, 11, 10, 12, 0, 0),
        error_code="auth",
        error_message="upstream 401 for sk-abcdef1234",
        retry_count=1,
        prompt=SECRET_PROMPT,
    )
    timeout_id = await _seed_call(
        sm,
        session_id=session_id,
        model_id=model_id,
        status="timeout",
        created_at=datetime(2026, 11, 10, 12, 1, 0),
        error_code="timeout",
        error_message="upstream request timed out",
        retry_count=0,
    )
    success_id = await _seed_call(
        sm,
        session_id=session_id,
        model_id=model_id,
        status="success",
        created_at=datetime(2026, 11, 10, 12, 2, 0),
        result_text="完整结果文本",
    )

    failed = await client.get(f"/api/v1/calls/{failed_id}")
    assert failed.status_code == 200
    body = failed.json()
    assert body["errorCode"] == "auth"
    assert body["retryCount"] == 1
    assert body["errorMessage"]
    assert "sk-abcdef1234" not in str(body)
    assert SECRET_PROMPT not in str(body)
    assert "sk-" not in str(body)

    timeout = await client.get(f"/api/v1/calls/{timeout_id}")
    assert timeout.status_code == 200
    assert timeout.json()["retryCount"] == 0
    assert timeout.json()["status"] == "timeout"

    success = await client.get(f"/api/v1/calls/{success_id}")
    assert success.status_code == 200
    assert success.json()["resultText"] == "完整结果文本"

    missing = await client.get("/api/v1/calls/999999")
    assert missing.status_code == 404
    assert missing.json()["code"] == "call_not_found"


@pytest.mark.asyncio
async def test_tc048_empty_result_not_error(client, database) -> None:
    sm = database.sessionmaker
    await _graph(sm)
    empty_project = await client.get("/api/v1/calls?projectId=999999")
    assert empty_project.status_code == 200
    assert empty_project.json() == {"items": [], "nextCursor": None}

    empty_range = await client.get(
        "/api/v1/calls?from=2020-01-01T00:00:00Z&to=2020-01-02T00:00:00Z"
    )
    assert empty_range.status_code == 200
    assert empty_range.json() == {"items": [], "nextCursor": None}

    inverted = await client.get(
        "/api/v1/calls?from=2026-11-11T00:00:00Z&to=2026-11-10T00:00:00Z"
    )
    assert inverted.status_code == 400
    assert inverted.json()["code"] == "validation_error"
