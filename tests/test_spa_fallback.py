"""SPA 静态托管与 API 未知路径的边界。

背景（2026-11-20 实测发现）：SPA 兜底原先注册成通配路由
``@app.get("/{full_path:path}")``。通配路由会参与匹配并抢占后注册的具体
路由，把未匹配的 ``/api/**`` 吞成 200 的 ``index.html``。这个 bug 平时
不显现——只有 ``web/dist`` 存在时才挂载兜底，而本地开发往往没构建前端，
所以一批 TC-029 / TC-060 / TC-061 / TC-071 长期「靠 dist 不存在才通过」。

修法：把兜底从通配路由改为 ``StarletteHTTPException`` 异常处理器，只在
「404 且非 API 路径且方法为 GET/HEAD」时返回 index.html。

本文件锁住三条边界，防止兜底再次抢走 API 的 404 / 405 / 400 / 500。
"""

from __future__ import annotations

import httpx
import pytest

from helpers import seed_admin
from workbench.main import WEB_DIST, create_app

pytestmark = pytest.mark.asyncio


from contextlib import asynccontextmanager


@asynccontextmanager
async def _client(settings, database, password: str = "spa-admin"):  # noqa: ANN001, ANN202
    await seed_admin(database.sessionmaker, password)
    app = create_app(settings=settings, database=database)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        await client.post(
            "/api/v1/auth/login",
            json={"password": password},
            headers={"origin": "http://testserver"},
        )
        yield client


@pytest.mark.skipif(not WEB_DIST.is_dir(), reason="需要 web/dist 存在才会挂载 SPA 兜底")
async def test_tc060_unknown_api_path_is_json_404_not_index_html(settings, database) -> None:
    """未知 API 端点必须是 404 JSON，不能被 SPA 兜底吞成 200 的 index.html。"""
    async with _client(settings, database) as client:
        response = await client.get("/api/v1/_definitely_missing")

    assert response.status_code == 404
    assert "application/json" in response.headers.get("content-type", "")
    assert set(response.json()) == {"code", "message", "details", "requestId"}


@pytest.mark.skipif(not WEB_DIST.is_dir(), reason="需要 web/dist 存在才会挂载 SPA 兜底")
async def test_tc060_spa_serves_index_for_frontend_routes(settings, database) -> None:
    """前端路由（非 API）仍由 SPA 兜底返回 index.html。"""
    async with _client(settings, database) as client:
        response = await client.get("/sessions", follow_redirects=False)

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.skipif(not WEB_DIST.is_dir(), reason="需要 web/dist 存在才会挂载 SPA 兜底")
async def test_tc060_missing_static_asset_is_404(settings, database) -> None:
    """缺失的静态资源必须 404，不能回退成 index.html。"""
    async with _client(settings, database) as client:
        response = await client.get("/assets/_missing.js")

    assert response.status_code == 404


@pytest.mark.skipif(not WEB_DIST.is_dir(), reason="需要 web/dist 存在才会挂载 SPA 兜底")
async def test_tc061_spa_does_not_bypass_origin_check(settings, database) -> None:
    """SPA 兜底不能绕过写端点的 Origin 校验（跨站请求仍应 403）。"""
    async with _client(settings, database) as client:
        response = await client.post(
            "/api/v1/projects",
            json={"name": "跨站项目"},
            headers={"origin": "https://evil.example"},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "forbidden_origin"
