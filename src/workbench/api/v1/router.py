"""`/api/v1` 路由汇总。"""

from __future__ import annotations

from fastapi import APIRouter

from workbench.api.v1 import artifacts, auth, calls, entrances, models, projects, providers, sessions

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(entrances.router)
api_router.include_router(projects.router)
api_router.include_router(providers.router)
api_router.include_router(models.router)
api_router.include_router(sessions.router)
api_router.include_router(artifacts.router)
api_router.include_router(calls.router)
