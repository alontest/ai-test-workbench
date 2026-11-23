"""连通性测试：保存后落状态、保存前零落库，结果固定四类。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime

from vigil_workbench.core.crypto import CredentialUnavailable
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.repos.constants import REPO_CONNECT_TIMEOUT_SECONDS
from vigil_workbench.repos.crypto import decrypt_token
from vigil_workbench.repos.providers import build_provider
from vigil_workbench.repos.providers.base import repository_ref
from vigil_workbench.repos.redaction import safe_log_fields
from vigil_workbench.repos.types import ProviderError, TestResult
from vigil_workbench.services.repos.binding_service import (
    repo_token_key,
    require_active_binding,
    validate_connection_inputs,
)

logger = logging.getLogger(__name__)

SUCCESS_MESSAGE = "连接成功。"
_TOKEN_INVALID_RESULTS = ("auth-error", "permission-denied")


@dataclass(frozen=True)
class _Probe:
    result: TestResult
    message: str
    default_branch: str | None = None
    token_expires_at: datetime | None = None
    retry_after_at: datetime | None = None


def _classify(category: str) -> TestResult:
    if category == "auth":
        return "auth-error"
    if category in ("permission_denied", "not_found"):
        return "permission-denied"
    return "unreachable"


def _failure(error: ProviderError) -> _Probe:
    return _Probe(
        result=_classify(error.category),
        message=error.message,
        retry_after_at=error.retry_after_at,
    )


async def _persist(binding_id: str, probe: _Probe, *, tested_at: datetime) -> str:
    async with get_sessionmaker()() as db:
        row = await require_active_binding(db, binding_id)
        row.last_verified_at = tested_at
        row.last_verify_result = probe.result
        row.last_verify_message = (
            None if probe.result == "success" else probe.message
        )
        if probe.result == "success":
            row.status = "connected"
            if probe.default_branch:
                row.default_branch = probe.default_branch
            row.token_expires_at = probe.token_expires_at
        elif probe.result in _TOKEN_INVALID_RESULTS:
            row.status = "token_invalid"
        row.updated_at = tested_at
        await db.commit()
        logger.info(
            "repo connectivity tested %s",
            safe_log_fields(
                {
                    "bindingId": row.binding_id,
                    "provider": row.provider,
                    "category": probe.result,
                }
            ),
        )
        return row.status


def _payload(
    probe: _Probe, *, binding_status: str | None, tested_at: datetime
) -> dict[str, object]:
    return {
        "result": probe.result,
        "testedAt": tested_at,
        "message": probe.message,
        "defaultBranch": probe.default_branch,
        "latestCommitAt": None,
        "retryAfterAt": probe.retry_after_at,
        "bindingStatus": binding_status,
    }


async def test_saved(
    binding_id: str, *, timeout: float = REPO_CONNECT_TIMEOUT_SECONDS
) -> dict[str, object]:
    async with get_sessionmaker()() as db:
        row = await require_active_binding(db, binding_id)
        ref = repository_ref(row)
        ciphertext = row.token_ciphertext

    tested_at = utcnow()
    try:
        token = decrypt_token(ciphertext, key=repo_token_key())
    except CredentialUnavailable:
        probe = _Probe("auth-error", ProviderError("auth").message)
    else:
        provider = build_provider(ref, token, timeout=timeout)
        try:
            async with asyncio.timeout(timeout):
                summary = await provider.get_repository(ref)
        except TimeoutError:
            probe = _failure(ProviderError("timeout"))
        except ProviderError as exc:
            probe = _failure(exc)
        else:
            probe = _Probe(
                result="success",
                message=SUCCESS_MESSAGE,
                default_branch=summary.default_branch,
                token_expires_at=provider.token_expires_at,
            )
        finally:
            await provider.aclose()

    status = await _persist(binding_id, probe, tested_at=tested_at)
    return _payload(probe, binding_status=status, tested_at=tested_at)


async def test_unsaved(
    *,
    provider: str,
    repo_identifier: str,
    org_id: str | None,
    api_base_url: str | None,
    token: str,
    timeout: float = REPO_CONNECT_TIMEOUT_SECONDS,
) -> dict[str, object]:
    """表单值直接测试：不开会话、不写任何行。"""
    ref = validate_connection_inputs(
        provider=provider,
        repo_identifier=repo_identifier,
        org_id=org_id,
        api_base_url=api_base_url,
        token=token,
    )
    tested_at = utcnow()
    provider_client = build_provider(ref, token, timeout=timeout)
    try:
        async with asyncio.timeout(timeout):
            summary = await provider_client.get_repository(ref)
    except TimeoutError:
        probe = _failure(ProviderError("timeout"))
    except ProviderError as exc:
        probe = _failure(exc)
    else:
        probe = _Probe(
            result="success",
            message=SUCCESS_MESSAGE,
            default_branch=summary.default_branch,
            token_expires_at=provider_client.token_expires_at,
        )
    finally:
        await provider_client.aclose()
    return _payload(probe, binding_status=None, tested_at=tested_at)


__all__ = ["build_provider", "test_saved", "test_unsaved"]
