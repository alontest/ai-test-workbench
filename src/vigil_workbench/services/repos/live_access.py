"""浏览与读文件共用的一次性供应商访问：状态守卫、令牌解密、错误映射。

所有实时端点在发起外呼前都要经过这里：已解绑 → 409、令牌不可用 → 502，
供应商 401/403/404 → 绑定置 ``token_invalid`` 后仍按 502 返回。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from typing import TypeVar

from vigil_workbench.core.crypto import CredentialUnavailable
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.repositories.repos import RepoRepository
from vigil_workbench.repos.crypto import decrypt_token
from vigil_workbench.repos.errors import RepoProviderError
from vigil_workbench.repos.providers import build_provider
from vigil_workbench.repos.providers.base import BaseProvider, repository_ref
from vigil_workbench.repos.redaction import safe_log_fields
from vigil_workbench.repos.types import ProviderError, RepositoryRef
from vigil_workbench.repos.validation import parse_repo_identifier
from vigil_workbench.services.repos.binding_service import (
    repo_token_key,
    require_active_binding,
)

logger = logging.getLogger(__name__)

TOKEN_INVALID_CATEGORIES = ("auth", "permission_denied", "not_found")

T = TypeVar("T")


@dataclass(frozen=True)
class LiveBinding:
    """一次实时访问所需的绑定快照；不携带令牌与密文原文。"""

    binding_id: str
    provider: str
    repo_key: str
    repo_name: str
    metadata_synced: bool
    ref: RepositoryRef
    token_ciphertext: str | None


async def load_live_binding(binding_id: str) -> LiveBinding:
    """404 ``binding_not_found`` / 409 ``binding_revoked``。"""
    async with get_sessionmaker()() as db:
        row = await require_active_binding(db, binding_id)
        return LiveBinding(
            binding_id=row.binding_id,
            provider=row.provider,
            repo_key=row.repo_key,
            repo_name=row.repo_name,
            metadata_synced=row.last_sync_success_at is not None,
            ref=repository_ref(row),
            token_ciphertext=row.token_ciphertext,
        )


def select_repository(live: LiveBinding, repo_id: str | None) -> RepositoryRef:
    """``repoId`` 可选；省略时使用绑定仓库。非法值 → 400。"""
    if not repo_id:
        return live.ref
    identifier = parse_repo_identifier(live.provider, repo_id)
    return replace(
        live.ref,
        repo_id=identifier.repo_id,
        repo_name=identifier.repo_name,
        owner=identifier.owner,
    )


async def mark_token_invalid(binding_id: str) -> None:
    """供应商返回 401/403/404 时把绑定置为 ``token_invalid``；已解绑不改。"""
    async with get_sessionmaker()() as db:
        row = await RepoRepository(db).get(binding_id)
        if row is None or row.status in ("revoked", "token_invalid"):
            return
        row.status = "token_invalid"
        row.updated_at = utcnow()
        await db.commit()
        logger.info(
            "repo binding marked token_invalid %s",
            safe_log_fields({"bindingId": row.binding_id, "provider": row.provider}),
        )


@asynccontextmanager
async def open_provider(live: LiveBinding) -> AsyncIterator[BaseProvider]:
    """解密令牌并构造适配器；密文缺失按鉴权失败处理。"""
    try:
        token = decrypt_token(live.token_ciphertext, key=repo_token_key())
    except CredentialUnavailable:
        await mark_token_invalid(live.binding_id)
        raise RepoProviderError(
            ProviderError("auth"),
            provider=live.provider,
            binding_id=live.binding_id,
        ) from None
    provider = build_provider(live.ref, token)
    try:
        yield provider
    finally:
        await provider.aclose()


async def run_provider_call(
    live: LiveBinding,
    operation: Callable[[], Awaitable[T]],
) -> T:
    """把 ``ProviderError`` 映射为固定 502；鉴权/权限/404 同时改绑定状态。"""
    try:
        return await operation()
    except ProviderError as exc:
        if exc.category in TOKEN_INVALID_CATEGORIES:
            await mark_token_invalid(live.binding_id)
        raise RepoProviderError(
            exc, provider=live.provider, binding_id=live.binding_id
        ) from None


__all__ = [
    "LiveBinding",
    "TOKEN_INVALID_CATEGORIES",
    "load_live_binding",
    "mark_token_invalid",
    "open_provider",
    "run_provider_call",
    "select_repository",
]
