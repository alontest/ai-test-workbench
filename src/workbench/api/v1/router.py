"""`/api/v1` 路由汇总。"""

from __future__ import annotations

from fastapi import APIRouter

from workbench.api.v1 import (
    artifacts,
    auth,
    calls,
    entrances,
    knowledge_bases,
    knowledge_entries,
    knowledge_injection,
    models,
    projects,
    providers,
    repo_bindings,
    repo_browse,
    sessions,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(entrances.router)
api_router.include_router(projects.router)
api_router.include_router(providers.router)
api_router.include_router(models.router)
api_router.include_router(sessions.router)
api_router.include_router(artifacts.router)
api_router.include_router(calls.router)
api_router.include_router(knowledge_bases.router)
api_router.include_router(knowledge_entries.router)
api_router.include_router(knowledge_injection.router)
api_router.include_router(repo_bindings.router)
api_router.include_router(repo_browse.router)
