"""登录/登出/会话接口与 HTML 跳转。用例名带 TC 编号。"""

from __future__ import annotations

from datetime import timedelta

import httpx
import pytest

from helpers import build_client, make_app, seed_admin
from workbench.config import Settings
from workbench.services import auth
from workbench.services.errors import DomainError

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


@pytest.fixture
async def app(settings, database):  # noqa: ANN001, ANN201
    application = make_app(settings, database)
    await seed_admin(database.sessionmaker, ADMIN)
    return application


@pytest.mark.asyncio
async def test_tc001_api_401_and_html_redirect(app) -> None:
    async with build_client(app) as client:
        for path in ("/api/v1/sessions", "/api/v1/projects", "/api/v1/providers", "/api/v1/calls"):
            response = await client.get(path)
            assert response.status_code == 401
            body = response.json()
            assert set(body) == {"code", "message", "details", "requestId"}
            assert body["code"] == "unauthorized"
            assert "Set-Cookie" not in response.headers

        response = await client.get("/sessions", headers={"accept": "text/html"})
        assert response.status_code == 302
        assert response.headers["location"].endswith("/login?next=%2Fsessions")
        assert "Set-Cookie" not in response.headers

        for token in ("forged", ""):
            response = await client.get(
                "/api/v1/auth/session", headers={"cookie": f"aw_session={token}"}
            )
            assert response.status_code == 401


@pytest.mark.asyncio
async def test_tc002_api_login_success(app) -> None:
    async with build_client(app) as client:
        response = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert response.status_code == 200
        assert response.json() == {"authenticated": True}
        cookie = response.headers["set-cookie"]
        assert cookie.startswith("aw_session=")
        assert ADMIN not in response.text

        wrong = await client.post(
            "/api/v1/auth/login", json={"password": "nope"}, headers=ORIGIN
        )
        assert wrong.status_code == 401
        assert wrong.json()["code"] == "login_failed"
        assert "set-cookie" not in wrong.headers


@pytest.mark.asyncio
async def test_tc007_api_logout_clears_cookie(app) -> None:
    async with build_client(app) as client:
        login = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        token = login.cookies["aw_session"]

        response = await client.post("/api/v1/auth/logout", headers=ORIGIN)
        assert response.status_code == 204
        assert response.text == ""
        cookie = response.headers["set-cookie"]
        assert "aw_session=" in cookie
        assert "max-age=0" in cookie.lower() or 'aw_session=""' in cookie

        stale = await client.get(
            "/api/v1/auth/session", headers={"cookie": f"aw_session={token}"}
        )
        assert stale.status_code == 401

        again = await client.post(
            "/api/v1/auth/logout",
            headers={**ORIGIN, "cookie": f"aw_session={token}"},
        )
        assert again.status_code == 401


@pytest.mark.asyncio
async def test_tc008_cookie_attributes(settings, database) -> None:
    await seed_admin(database.sessionmaker, ADMIN)

    insecure = Settings(cookie_secure="false")
    async with build_client(make_app(insecure, database)) as client:
        response = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie or "SameSite=Lax" in cookie
        assert "Path=/" in cookie
        assert "Secure" not in cookie

    secure = Settings(cookie_secure="true")
    async with build_client(make_app(secure, database), base_url="https://testserver") as client:
        response = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert "Secure" in response.headers["set-cookie"]

    auto = Settings(cookie_secure="auto")
    async with build_client(make_app(auto, database), base_url="https://testserver") as client:
        response = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert "Secure" in response.headers["set-cookie"]


@pytest.mark.asyncio
async def test_tc008_logout_cookie_attributes(settings, database) -> None:
    """登出删除 Cookie 时属性与登录下发一致（HttpOnly / SameSite / Path / Secure）。"""
    await seed_admin(database.sessionmaker, ADMIN)

    insecure = Settings(cookie_secure="false")
    async with build_client(make_app(insecure, database)) as client:
        await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        response = await client.post("/api/v1/auth/logout", headers=ORIGIN)
        assert response.status_code == 204
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie or "SameSite=Lax" in cookie
        assert "Path=/" in cookie
        assert "Secure" not in cookie

    secure = Settings(cookie_secure="true")
    async with build_client(
        make_app(secure, database), base_url="https://testserver"
    ) as client:
        await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        response = await client.post("/api/v1/auth/logout", headers=ORIGIN)
        assert response.status_code == 204
        cookie = response.headers["set-cookie"]
        assert "HttpOnly" in cookie
        assert "Path=/" in cookie
        assert "Secure" in cookie


@pytest.mark.asyncio
async def test_tc010_login_next_is_internal_only(app) -> None:
    async with build_client(app) as client:
        response = await client.get(
            "/sessions/42?tab=timeline", headers={"accept": "text/html"}
        )
        assert response.status_code == 302
        assert (
            response.headers["location"]
            == "/login?next=%2Fsessions%2F42%3Ftab%3Dtimeline"
        )

        from workbench.api.v1.auth import safe_next_path

        assert safe_next_path("/providers") == "/providers"
        assert safe_next_path(None) == "/"
        for hostile in (
            "https://evil.example",
            "//evil.example",
            "/\\evil.example",
            "javascript:alert(1)",
            "%2F%2Fevil",
            "\r\n/x",
        ):
            assert safe_next_path(hostile) == "/"


@pytest.mark.asyncio
async def test_tc011_expired_session_redirects(app, monkeypatch) -> None:
    async with build_client(app) as client:
        await client.post("/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN)
        future = auth.utcnow() + timedelta(hours=8, seconds=1)
        monkeypatch.setattr(auth, "utcnow", lambda: future)

        response = await client.get("/api/v1/auth/session")
        assert response.status_code == 401
        assert set(response.json()) == {"code", "message", "details", "requestId"}

        page = await client.get("/sessions", headers={"accept": "text/html"})
        assert page.status_code == 302
        assert page.headers["location"] == "/login?next=%2Fsessions"


@pytest.mark.asyncio
async def test_tc012_next_rejects_external_url(app) -> None:
    from workbench.api.v1.auth import safe_next_path

    assert safe_next_path("%2F%2Fevil") == "/"
    assert safe_next_path("//evil.example") == "/"
    assert safe_next_path("") == "/"
    assert safe_next_path("/sessions/1?tab=a%20b") == "/sessions/1?tab=a%20b"


@pytest.mark.asyncio
async def test_tc061_origin_check_rejects_cross_site(app) -> None:
    async with build_client(app) as client:
        missing = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}
        )
        assert missing.status_code == 403
        assert missing.json()["code"] == "forbidden_origin"

        evil = await client.post(
            "/api/v1/auth/login",
            json={"password": ADMIN},
            headers={"origin": "https://evil.example"},
        )
        assert evil.status_code == 403

        same = await client.post(
            "/api/v1/auth/login", json={"password": ADMIN}, headers=ORIGIN
        )
        assert same.status_code == 200

        referer = await client.post(
            "/api/v1/auth/login",
            json={"password": ADMIN},
            headers={"referer": "http://testserver/login"},
        )
        assert referer.status_code == 200

        async with build_client(app) as fresh:
            get = await fresh.get("/api/v1/auth/session")
            assert get.status_code == 401

        null_origin = await client.post(
            "/api/v1/auth/login",
            json={"password": ADMIN},
            headers={"origin": "null"},
        )
        assert null_origin.status_code == 403
