"""绑定生命周期：输入校验、密文落库、唯一性、列表、令牌更新与解绑。"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from workbench.config import get_settings
from workbench.db.base import utcnow
from workbench.db.engine import get_sessionmaker
from workbench.db.errors import is_unique_violation
from workbench.db.models import RepoBinding, RepoMetadataSnapshot
from workbench.db.repositories import projects as projects_repo
from workbench.db.repositories.repos import RepoRepository
from workbench.repos.cursor import (
    decode_page_cursor,
    derive_cursor_key,
    encode_page_cursor,
)
from workbench.repos.crypto import encrypt_token, mask_token
from workbench.repos.errors import RepoDomainError, RepoValidationError
from workbench.repos.redaction import safe_log_fields
from workbench.repos.types import RepositoryRef
from workbench.repos.validation import (
    YUNXIAO_API_BASE_URL,
    normalize_repo_key,
    parse_repo_identifier,
    validate_api_base_url,
    validate_provider,
)
from workbench.services.repos.serializers import serialize_binding

logger = logging.getLogger(__name__)

TOKEN_MAX_LENGTH = 1024
DUPLICATE_MESSAGE = "同一项目下已存在该仓库绑定。"
DUPLICATE_DETAIL = "同一提供商与仓库已绑定，原绑定与令牌不变。"
TOKEN_REQUIRED_MESSAGE = "令牌不能为空。"
REVOKED_MESSAGE = "绑定已解绑，请重新绑定。"


def repo_token_key() -> bytes:
    return get_settings().repo_token_key_bytes


def repo_cursor_key() -> bytes:
    return derive_cursor_key(repo_token_key())


def validate_token(token: str) -> str:
    text = token.strip() if isinstance(token, str) else ""
    if not text:
        raise RepoValidationError(
            "token_required",
            TOKEN_REQUIRED_MESSAGE,
            details=[{"field": "token", "message": TOKEN_REQUIRED_MESSAGE}],
        )
    if len(token) > TOKEN_MAX_LENGTH:
        raise RepoValidationError(
            "validation_error",
            "请求参数校验失败。",
            details=[
                {
                    "field": "token",
                    "message": f"令牌长度不能超过 {TOKEN_MAX_LENGTH}。",
                }
            ],
        )
    return token


def _resolve_api_base_url(provider: str, api_base_url: str | None) -> str:
    if provider == "github":
        return validate_api_base_url(provider, api_base_url)
    candidate = api_base_url.strip() if isinstance(api_base_url, str) else ""
    if not candidate or candidate.rstrip("/") == YUNXIAO_API_BASE_URL:
        return YUNXIAO_API_BASE_URL
    return validate_api_base_url(provider, candidate)


def validate_connection_inputs(
    *,
    provider: str,
    repo_identifier: str,
    org_id: str | None,
    api_base_url: str | None,
    token: str,
) -> RepositoryRef:
    """按 api-spec 优先级校验：provider → orgId → 标识 → 域名 → 令牌。"""
    cleaned_provider = validate_provider(provider)
    org = org_id.strip() if isinstance(org_id, str) else None
    if cleaned_provider == "yunxiao" and not org:
        raise RepoValidationError(
            "validation_error",
            "请求参数校验失败。",
            details=[{"field": "orgId", "message": "云效需要组织 ID。"}],
        )
    if cleaned_provider == "github":
        org = None
    identifier = parse_repo_identifier(cleaned_provider, repo_identifier)
    origin = _resolve_api_base_url(cleaned_provider, api_base_url)
    validate_token(token)
    return RepositoryRef(
        provider=cleaned_provider,
        repo_id=identifier.repo_id,
        repo_name=identifier.repo_name,
        api_base_url=origin,
        org_id=org,
        owner=identifier.owner,
    )


def _not_found(code: str, message: str) -> RepoDomainError:
    return RepoDomainError(code, message, status_code=404)


async def require_project(db: AsyncSession, project_id: int) -> None:
    if await projects_repo.get(db, project_id) is None:
        raise _not_found("project_not_found", "项目不存在。")


async def require_binding(db: AsyncSession, binding_id: str) -> RepoBinding:
    row = await RepoRepository(db).get(binding_id)
    if row is None:
        raise _not_found("binding_not_found", "仓库绑定不存在。")
    return row


async def require_active_binding(db: AsyncSession, binding_id: str) -> RepoBinding:
    row = await require_binding(db, binding_id)
    if row.status == "revoked":
        raise RepoDomainError("binding_revoked", REVOKED_MESSAGE, status_code=409)
    return row


def _duplicate() -> RepoDomainError:
    return RepoDomainError(
        "repo_binding_duplicate",
        DUPLICATE_MESSAGE,
        status_code=409,
        details=[{"field": "repoIdentifier", "message": DUPLICATE_DETAIL}],
    )


def _binding_shape(ref: RepositoryRef) -> dict[str, Any]:
    return {
        "provider": ref.provider,
        "api_base_url": ref.api_base_url,
        "org_id": ref.org_id,
        "owner": ref.owner,
        "repo_id": ref.repo_id,
        "repo_name": ref.repo_name,
        "display_name": ref.repo_name,
    }


async def create_binding(
    *,
    project_id: int,
    provider: str,
    repo_identifier: str,
    org_id: str | None,
    api_base_url: str | None,
    token: str,
) -> dict[str, object]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await require_project(db, project_id)
        ref = validate_connection_inputs(
            provider=provider,
            repo_identifier=repo_identifier,
            org_id=org_id,
            api_base_url=api_base_url,
            token=token,
        )
        repo = RepoRepository(db)
        repo_key = normalize_repo_key(ref.provider, ref.repo_name)
        if await repo.find_active(
            project_id=project_id, provider=ref.provider, repo_key=repo_key
        ) is not None:
            raise _duplicate()

        now = utcnow()
        row = RepoBinding(
            binding_id=uuid4().hex,
            project_id=project_id,
            repo_key=repo_key,
            token_ciphertext=encrypt_token(token, key=repo_token_key()),
            token_masked=mask_token(token),
            status="unverified",
            active_flag="1",
            created_at=now,
            updated_at=now,
            **_binding_shape(ref),
        )
        db.add(row)
        try:
            await db.commit()
        except DBAPIError as exc:
            await db.rollback()
            if is_unique_violation(exc):
                raise _duplicate() from exc
            raise
        await db.refresh(row)
        logger.info(
            "repo binding created %s",
            safe_log_fields(
                {"bindingId": row.binding_id, "provider": row.provider, "repoKey": repo_key}
            ),
        )
        return serialize_binding(row)


async def _latest_baseline(
    repo: RepoRepository, binding_id: str
) -> RepoMetadataSnapshot | None:
    snapshots = await repo.latest_repo_snapshots([binding_id])
    return snapshots.get(binding_id)


async def list_bindings(
    project_id: int, *, limit: int, cursor: str | None
) -> tuple[list[dict[str, object]], str | None]:
    key = repo_cursor_key()
    context = {
        "binding_id": "",
        "provider": "",
        "repo_key": f"project:{project_id}",
    }
    page = (
        decode_page_cursor(cursor, key=key, **context) if cursor else 1
    )
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        await require_project(db, project_id)
        repo = RepoRepository(db)
        rows = await repo.list_for_project(
            project_id,
            limit=limit + 1,
            offset=(page - 1) * limit,
        )
        page_rows = rows[:limit]
        snapshots = await repo.latest_repo_snapshots(
            [row.binding_id for row in page_rows]
        )
    has_more = len(rows) > limit
    items = [
        serialize_binding(row, baseline=snapshots.get(row.binding_id))
        for row in page_rows
    ]
    next_cursor = None
    if has_more and page_rows:
        next_cursor = encode_page_cursor(key=key, page=page + 1, **context)
    return items, next_cursor


async def get_binding(binding_id: str) -> dict[str, object]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await require_binding(db, binding_id)
        baseline = await _latest_baseline(RepoRepository(db), binding_id)
        return serialize_binding(row, baseline=baseline)


async def update_token(binding_id: str, *, token: str) -> dict[str, object]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await require_binding(db, binding_id)
        if row.status == "revoked":
            raise RepoDomainError("binding_revoked", REVOKED_MESSAGE, status_code=409)
        validate_token(token)
        await RepoRepository(db).update_token(
            binding_id,
            ciphertext=encrypt_token(token, key=repo_token_key()),
            masked=mask_token(token),
        )
        await db.commit()
        await db.refresh(row)
        baseline = await _latest_baseline(RepoRepository(db), binding_id)
        logger.info(
            "repo binding token updated %s",
            safe_log_fields({"bindingId": row.binding_id, "provider": row.provider}),
        )
        return serialize_binding(row, baseline=baseline)


async def unbind(binding_id: str) -> dict[str, object]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        row = await require_binding(db, binding_id)
        if row.status != "revoked":
            await RepoRepository(db).unbind(binding_id)
            await db.commit()
            await db.refresh(row)
            logger.info(
                "repo binding revoked %s",
                safe_log_fields(
                    {"bindingId": row.binding_id, "provider": row.provider}
                ),
            )
        baseline = await _latest_baseline(RepoRepository(db), binding_id)
        return serialize_binding(row, baseline=baseline)


__all__ = [
    "create_binding",
    "get_binding",
    "list_bindings",
    "repo_cursor_key",
    "repo_token_key",
    "require_active_binding",
    "require_binding",
    "require_project",
    "unbind",
    "update_token",
    "validate_connection_inputs",
    "validate_token",
]
