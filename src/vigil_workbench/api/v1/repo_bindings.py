"""仓库绑定接口：端点 1~9（列表、创建、详情、令牌、连通性、同步、记录、解绑）。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.api.serialization import to_rfc3339
from vigil_workbench.api.schemas.repo import (
    RepoBindingCreate,
    RepoConnectionTest,
    RepoTokenUpdate,
)
from vigil_workbench.services.repos import (
    binding_service,
    connectivity_service,
    sync_service,
)

router = APIRouter(
    tags=["repo-bindings"],
    dependencies=[Depends(require_same_origin)],
)


def _as_time(value: object) -> str | None:
    return to_rfc3339(value) if isinstance(value, datetime) else None


def _connection_response(result: dict[str, object]) -> dict[str, object]:
    return {
        "result": result["result"],
        "testedAt": _as_time(result.get("testedAt")),
        "message": result["message"],
        "defaultBranch": result.get("defaultBranch"),
        "latestCommitAt": _as_time(result.get("latestCommitAt")),
        "retryAfterAt": _as_time(result.get("retryAfterAt")),
        "bindingStatus": result.get("bindingStatus"),
    }


@router.get("/projects/{project_id}/repo-bindings")
async def list_repo_bindings(
    project_id: int,
    limit: int = Query(30, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    items, next_cursor = await binding_service.list_bindings(
        project_id, limit=limit, cursor=cursor
    )
    return {"items": items, "nextCursor": next_cursor}


@router.post("/projects/{project_id}/repo-bindings", status_code=201)
async def create_repo_binding(
    project_id: int, payload: RepoBindingCreate
) -> dict[str, object]:
    return await binding_service.create_binding(
        project_id=project_id,
        provider=payload.provider,
        repo_identifier=payload.repo_identifier,
        org_id=payload.org_id,
        api_base_url=payload.api_base_url,
        token=payload.token,
    )


# 静态路径必须排在动态 /{binding_id} 之前。
@router.post("/repo-bindings/test-connection")
async def test_connection_unsaved(
    payload: RepoConnectionTest,
) -> dict[str, object]:
    result = await connectivity_service.test_unsaved(
        provider=payload.provider,
        repo_identifier=payload.repo_identifier,
        org_id=payload.org_id,
        api_base_url=payload.api_base_url,
        token=payload.token,
    )
    return _connection_response(result)


@router.get("/repo-bindings/{binding_id}")
async def get_repo_binding(binding_id: str) -> dict[str, object]:
    return await binding_service.get_binding(binding_id)


@router.patch("/repo-bindings/{binding_id}/token")
async def update_repo_binding_token(
    binding_id: str, payload: RepoTokenUpdate
) -> dict[str, object]:
    return await binding_service.update_token(binding_id, token=payload.token)


@router.post("/repo-bindings/{binding_id}/test-connection")
async def test_connection_saved(binding_id: str) -> dict[str, object]:
    result = await connectivity_service.test_saved(binding_id)
    return _connection_response(result)


@router.post("/repo-bindings/{binding_id}/unbind")
async def unbind_repo_binding(binding_id: str) -> dict[str, object]:
    return await binding_service.unbind(binding_id)


@router.post("/repo-bindings/{binding_id}/sync")
async def sync_repo_binding(binding_id: str) -> dict[str, object]:
    return await sync_service.sync_binding(binding_id)


@router.get("/repo-bindings/{binding_id}/sync-records")
async def list_repo_sync_records(
    binding_id: str,
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = None,
) -> dict[str, object]:
    items, next_cursor = await sync_service.list_sync_records(
        binding_id, limit=limit, cursor=cursor
    )
    return {"items": items, "nextCursor": next_cursor}
