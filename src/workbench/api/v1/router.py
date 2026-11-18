"""`/api/v1` 路由汇总。

批次 A 只建立挂载点；业务端点在后续批次注册。
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
