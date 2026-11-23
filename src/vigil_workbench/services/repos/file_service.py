"""按需读取单个文件：前置校验 → 读取 → 大小/编码判定 → 审计（ADR-210 / ADR-213）。

判定顺序：路径 / ref 校验（不发外呼、不写记录）→ 绑定状态 → 供应商读取 →
``size`` 与解码后字节数（413）→ NUL（415）→ UTF-8（422）。拒绝不截断，
正文不入库、不入日志。
"""

from __future__ import annotations

import base64
import binascii
from datetime import datetime

from vigil_workbench.api.serialization import to_rfc3339
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.models import RepoFileReadRecord
from vigil_workbench.repos.constants import REPO_FILE_MAX_BYTES
from vigil_workbench.repos.errors import (
    RepoProviderError,
    file_binary,
    file_not_utf8,
    file_too_large,
)
from vigil_workbench.repos.providers.base import FileTooLarge
from vigil_workbench.repos.types import FileContent, ProviderError, RepositoryRef
from vigil_workbench.repos.validation import validate_ref, validate_repo_path
from vigil_workbench.services.repos.live_access import (
    LiveBinding,
    load_live_binding,
    open_provider,
    run_provider_call,
    select_repository,
)
from vigil_workbench.services.repos.serializers import serialize_file

TOO_LARGE = "too_large"
BINARY = "binary"
NOT_UTF8 = "not_utf8"


def _repo_id(selected: RepositoryRef) -> str:
    return selected.repo_id or selected.repo_name


async def _write_record(
    live: LiveBinding,
    selected: RepositoryRef,
    *,
    ref: str,
    path: str,
    size_bytes: int | None,
    encoding: str,
    status: str,
    reject_reason: str | None,
    fetched_at: datetime,
) -> None:
    async with get_sessionmaker()() as db:
        db.add(
            RepoFileReadRecord(
                binding_id=live.binding_id,
                repo_id=_repo_id(selected),
                ref=ref,
                file_path=path,
                byte_size=size_bytes,
                encoding=encoding,
                status=status,
                reject_reason=reject_reason,
                fetched_at=fetched_at,
            )
        )
        await db.commit()


async def _refuse(
    live: LiveBinding,
    selected: RepositoryRef,
    *,
    ref: str,
    path: str,
    size_bytes: int | None,
    encoding: str,
    reason: str,
    fetched_at: datetime,
) -> None:
    await _write_record(
        live,
        selected,
        ref=ref,
        path=path,
        size_bytes=size_bytes,
        encoding=encoding,
        status="refused",
        reject_reason=reason,
        fetched_at=fetched_at,
    )


def _decode(content: FileContent, live: LiveBinding) -> bytes:
    if content.encoding != "base64":
        return content.content.encode("utf-8")
    try:
        return base64.b64decode(content.content, validate=True)
    except (binascii.Error, ValueError):
        raise RepoProviderError(
            ProviderError("invalid_response"),
            provider=live.provider,
            binding_id=live.binding_id,
        ) from None


async def read_file(
    binding_id: str, *, repo_id: str | None, ref: str, path: str
) -> dict[str, object]:
    # 前置校验必须早于任何数据库写入与外部请求（AC-022-5）。
    validate_ref(ref)
    validate_repo_path(path)

    live = await load_live_binding(binding_id)
    selected = select_repository(live, repo_id)
    fetched_at = utcnow()

    async with open_provider(live) as provider:
        try:
            content = await run_provider_call(
                live, lambda: provider.read_file(selected, ref=ref, path=path)
            )
        except FileTooLarge as exc:
            await _refuse(
                live,
                selected,
                ref=ref,
                path=path,
                size_bytes=exc.size_bytes,
                encoding=exc.encoding,
                reason=TOO_LARGE,
                fetched_at=fetched_at,
            )
            raise file_too_large(exc.size_bytes, exc.limit_bytes) from None

    raw = _decode(content, live)
    if content.size_bytes > REPO_FILE_MAX_BYTES or len(raw) > REPO_FILE_MAX_BYTES:
        actual = max(content.size_bytes, len(raw))
        await _refuse(
            live,
            selected,
            ref=ref,
            path=path,
            size_bytes=actual,
            encoding=content.encoding,
            reason=TOO_LARGE,
            fetched_at=fetched_at,
        )
        raise file_too_large(actual, REPO_FILE_MAX_BYTES)

    if b"\x00" in raw:
        await _refuse(
            live,
            selected,
            ref=ref,
            path=path,
            size_bytes=len(raw),
            encoding=content.encoding,
            reason=BINARY,
            fetched_at=fetched_at,
        )
        raise file_binary()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        await _refuse(
            live,
            selected,
            ref=ref,
            path=path,
            size_bytes=len(raw),
            encoding=content.encoding,
            reason=NOT_UTF8,
            fetched_at=fetched_at,
        )
        raise file_not_utf8() from None

    await _write_record(
        live,
        selected,
        ref=ref,
        path=path,
        size_bytes=content.size_bytes,
        encoding=content.encoding,
        status="success",
        reject_reason=None,
        fetched_at=fetched_at,
    )
    return serialize_file(
        FileContent(
            path=content.path,
            ref=content.ref,
            size_bytes=content.size_bytes,
            encoding="text",
            content=text,
            fetched_at=content.fetched_at,
        ),
        fetched_at=to_rfc3339(fetched_at),
    )


__all__ = ["read_file"]
