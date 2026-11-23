"""仓库浏览与读文件接口：端点 10~15（实时浏览、单文件、跨域只读基线）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.repos.constants import REPO_PAGE_DEFAULT, REPO_PAGE_MAX, REPO_TREE_PAGE_LIMIT
from vigil_workbench.services.repos import browse_service, file_service

router = APIRouter(
    tags=["repo-browse"],
    dependencies=[Depends(require_same_origin)],
)


@router.get("/repo-bindings/{binding_id}/repositories")
async def list_live_repositories(
    binding_id: str,
    search: str | None = None,
    limit: int = Query(REPO_PAGE_DEFAULT, ge=1, le=REPO_PAGE_MAX),
    cursor: str | None = None,
) -> dict[str, object]:
    return await browse_service.list_repositories(
        binding_id, search=search, limit=limit, cursor=cursor
    )


@router.get("/repo-bindings/{binding_id}/branches")
async def list_live_branches(
    binding_id: str,
    repo_id: str | None = Query(None, alias="repoId"),
    search: str | None = None,
    limit: int = Query(REPO_PAGE_DEFAULT, ge=1, le=REPO_PAGE_MAX),
    cursor: str | None = None,
) -> dict[str, object]:
    return await browse_service.list_branches(
        binding_id,
        repo_id=repo_id,
        search=search,
        limit=limit,
        cursor=cursor,
    )


@router.get("/repo-bindings/{binding_id}/commits")
async def list_live_commits(
    binding_id: str,
    ref: str = Query(...),
    repo_id: str | None = Query(None, alias="repoId"),
    limit: int = Query(REPO_PAGE_DEFAULT, ge=1, le=REPO_PAGE_MAX),
    cursor: str | None = None,
) -> dict[str, object]:
    return await browse_service.list_commits(
        binding_id,
        repo_id=repo_id,
        ref=ref,
        limit=limit,
        cursor=cursor,
    )


@router.get("/repo-bindings/{binding_id}/tree")
async def list_live_tree(
    binding_id: str,
    ref: str = Query(...),
    path: str = "",
    repo_id: str | None = Query(None, alias="repoId"),
    limit: int = Query(REPO_TREE_PAGE_LIMIT, ge=1, le=REPO_PAGE_MAX),
    cursor: str | None = None,
) -> dict[str, object]:
    return await browse_service.list_tree(
        binding_id,
        repo_id=repo_id,
        ref=ref,
        path=path,
        limit=limit,
        cursor=cursor,
    )


@router.get("/repo-bindings/{binding_id}/file")
async def read_repo_file(
    binding_id: str,
    ref: str = Query(...),
    path: str = Query(...),
    repo_id: str | None = Query(None, alias="repoId"),
) -> dict[str, object]:
    return await file_service.read_file(
        binding_id, repo_id=repo_id, ref=ref, path=path
    )


@router.get("/repo-bindings/{binding_id}/baseline")
async def read_repo_baseline(binding_id: str) -> dict[str, object]:
    return await browse_service.read_baseline(binding_id)
