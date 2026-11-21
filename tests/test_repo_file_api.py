"""读文件 API：成功、超限、二进制、非 UTF-8、前置校验与解绑守卫。用例名带 TC 编号。"""

from __future__ import annotations

import base64
import re
import uuid
from typing import Any, Callable

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import func, select

from helpers import build_client, make_app, seed_admin, seed_project
from workbench.db.models import RepoFileReadRecord
from workbench.repos.constants import REPO_FILE_MAX_BYTES
from workbench.repos.providers.github import GitHubProvider
from workbench.services.repos import live_access

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}
RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def binding_url(binding_id: str) -> str:
    return f"/api/v1/repo-bindings/{binding_id}"


def token(suffix: str = "abcd") -> str:
    return f"ghp_RISENTINEL_{uuid.uuid4().hex}_{suffix}"


def install_transport(
    monkeypatch,
    handler: Callable[[httpx.Request], httpx.Response],
) -> list[httpx.Request]:
    calls: list[httpx.Request] = []

    def factory(ref, token_value):  # noqa: ANN001, ANN202
        def wrapped(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        return GitHubProvider(ref, token_value, transport=httpx.MockTransport(wrapped))

    monkeypatch.setattr(live_access, "build_provider", factory)
    return calls


@pytest_asyncio.fixture
async def api(settings, database):  # noqa: ANN001, ANN201
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings=settings, database=database)
    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert login.status_code == 200
        project_id = await seed_project(database.sessionmaker)
        yield client, database, settings, project_id


async def create_binding(
    client, project_id: int, *, repo: str = "pay/checkout"
) -> tuple[str, str]:
    sentinel = token()
    response = await client.post(
        f"/api/v1/projects/{project_id}/repo-bindings",
        json={"provider": "github", "repoIdentifier": repo, "token": sentinel},
        headers=ORIGIN,
    )
    assert response.status_code == 201, response.text
    return response.json()["bindingId"], sentinel


def file_blob(raw: bytes, *, encoding: str = "base64", size: int | None = None) -> dict[str, Any]:
    return {
        "name": "main.py",
        "path": "src/main.py",
        "size": len(raw) if size is None else size,
        "encoding": encoding,
        "content": base64.b64encode(raw).decode() if encoding == "base64" else raw.decode(),
    }


async def read_rows(database, binding_id: str) -> list[RepoFileReadRecord]:  # noqa: ANN001
    async with database.sessionmaker() as db:
        rows = await db.scalars(
            select(RepoFileReadRecord).where(
                RepoFileReadRecord.binding_id == binding_id
            )
        )
        return list(rows)


async def read_count(database, binding_id: str) -> int:  # noqa: ANN001
    async with database.sessionmaker() as db:
        return (
            await db.scalar(
                select(func.count())
                .select_from(RepoFileReadRecord)
                .where(RepoFileReadRecord.binding_id == binding_id)
            )
        ) or 0


@pytest.mark.asyncio
async def test_tc235_file_read_success_records_metadata_only(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, sentinel = await create_binding(client, project_id)
    raw = "print('hello')\n".encode()
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=file_blob(raw))
    )

    response = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/main.py"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["path"] == "src/main.py"
    assert body["ref"] == "main"
    assert body["sizeBytes"] == len(raw)
    assert body["encoding"] == "text"
    assert body["content"] == raw.decode()
    assert RFC3339.match(body["fetchedAt"])

    assert len(calls) == 1
    assert calls[0].url.path == "/repos/pay/checkout/contents/src/main.py"
    assert calls[0].url.params["ref"] == "main"
    assert sentinel not in response.text

    rows = await read_rows(database, binding_id)
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "success"
    assert row.reject_reason is None
    assert row.repo_id == "pay/checkout"
    assert row.ref == "main"
    assert row.file_path == "src/main.py"
    assert row.byte_size == len(raw)
    assert row.encoding == "base64"
    assert "hello" not in repr(row.__dict__)


@pytest.mark.asyncio
async def test_tc236_file_too_large_rejected_without_truncation(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    actual = REPO_FILE_MAX_BYTES + 1
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            200,
            json={"size": actual, "encoding": "none", "content": ""},
        ),
    )

    response = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/big.bin"
    )
    assert response.status_code == 413, response.text
    body = response.json()
    assert body["code"] == "repo_file_too_large"
    assert "content" not in body
    detail = body["details"][0]
    assert detail["field"] == "sizeBytes"
    assert str(actual) in detail["message"]
    assert str(REPO_FILE_MAX_BYTES) in detail["message"]

    rows = await read_rows(database, binding_id)
    assert len(rows) == 1
    assert rows[0].status == "refused"
    assert rows[0].reject_reason == "too_large"
    assert rows[0].byte_size == actual
    assert rows[0].encoding == "base64"


@pytest.mark.asyncio
async def test_tc237_binary_content_rejected(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    raw = b"\x00\x01binary-body-sentinel"
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(200, json=file_blob(raw)),
    )

    response = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/blob.bin"
    )
    assert response.status_code == 415, response.text
    body = response.json()
    assert body["code"] == "repo_file_binary"
    assert "binary-body-sentinel" not in response.text

    rows = await read_rows(database, binding_id)
    assert len(rows) == 1
    assert rows[0].status == "refused"
    assert rows[0].reject_reason == "binary"
    assert rows[0].byte_size == len(raw)


@pytest.mark.asyncio
async def test_tc238_non_utf8_rejected(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    raw = b"\xff\xfe\xfd"
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(200, json=file_blob(raw)),
    )

    response = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/latin1.txt"
    )
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "repo_file_not_utf8"
    assert "�" not in response.text
    assert "content" not in body

    rows = await read_rows(database, binding_id)
    assert len(rows) == 1
    assert rows[0].status == "refused"
    assert rows[0].reject_reason == "not_utf8"


@pytest.mark.asyncio
async def test_tc239_invalid_path_or_ref_rejected_before_request(
    api, monkeypatch
) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=file_blob(b"x"))
    )
    before = await read_count(database, binding_id)

    for path in ("../etc/passwd", "/etc/passwd", "src/\x00main.py", "a" * 1025):
        response = await client.get(
            f"{binding_url(binding_id)}/file",
            params={"ref": "main", "path": path},
        )
        assert response.status_code == 400, response.text
        assert response.json()["code"] == "invalid_path"

    for ref in ("a..b", "main\n", "@{upstream}", "a b"):
        response = await client.get(
            f"{binding_url(binding_id)}/file",
            params={"ref": ref, "path": "src/main.py"},
        )
        assert response.status_code == 400, response.text
        assert response.json()["code"] == "invalid_ref"

    # 非法路径优先于资源存在性，且不产生任何外呼或读取记录。
    missing = await client.get(
        "/api/v1/repo-bindings/" + "0" * 32 + "/file",
        params={"ref": "main", "path": "../escape"},
    )
    assert missing.status_code == 400
    assert missing.json()["code"] == "invalid_path"

    assert calls == []
    assert await read_count(database, binding_id) == before


@pytest.mark.asyncio
async def test_tc240_file_read_on_revoked_binding_409(api, monkeypatch) -> None:
    client, database, _, project_id = api
    binding_id, _ = await create_binding(client, project_id)
    unbound = await client.post(f"{binding_url(binding_id)}/unbind", headers=ORIGIN)
    assert unbound.status_code == 200, unbound.text
    calls = install_transport(
        monkeypatch, lambda request: httpx.Response(200, json=file_blob(b"x"))
    )

    response = await client.get(
        f"{binding_url(binding_id)}/file?ref=main&path=src/main.py"
    )
    assert response.status_code == 409, response.text
    assert response.json()["code"] == "binding_revoked"
    assert calls == []
    assert await read_count(database, binding_id) == 0
