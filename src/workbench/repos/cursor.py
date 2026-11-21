"""不透明分页游标：base64url(JSON) + HMAC-SHA256(16B)（ADR-208）。"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
from typing import Any

from workbench.repos.errors import RepoValidationError

CURSOR_VERSION = 1
SIGNATURE_BYTES = 16
INVALID_CURSOR_MESSAGE = "分页游标无效。"

_CONTEXT_KEYS = ("b", "p", "r", "ref", "path", "qfp")


def derive_cursor_key(key: bytes) -> bytes:
    return hashlib.sha256(b"cursor:" + key).digest()


def fingerprint_query(search: str | None) -> str:
    text = search.strip() if isinstance(search, str) else ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding, altchars=b"-_", validate=True)


def _signature(key: bytes, body: bytes) -> bytes:
    return hmac.new(key, body, hashlib.sha256).digest()[:SIGNATURE_BYTES]


def _invalid() -> RepoValidationError:
    return RepoValidationError(
        "invalid_cursor",
        INVALID_CURSOR_MESSAGE,
        details=[{"field": "cursor", "message": INVALID_CURSOR_MESSAGE}],
    )


def encode_page_cursor(
    *,
    key: bytes,
    binding_id: str,
    provider: str,
    repo_key: str,
    ref: str | None = None,
    path: str | None = None,
    query_fingerprint: str = "",
    page: int,
) -> str:
    if page < 1:
        raise ValueError("page must be >= 1")
    payload: dict[str, Any] = {
        "v": CURSOR_VERSION,
        "b": binding_id,
        "p": provider,
        "r": repo_key,
        "ref": ref,
        "path": path,
        "qfp": query_fingerprint,
        "page": page,
    }
    body = json.dumps(
        payload, separators=(",", ":"), ensure_ascii=False, sort_keys=True
    ).encode("utf-8")
    return f"{_b64encode(body)}.{_b64encode(_signature(key, body))}"


def decode_page_cursor(
    cursor: str,
    *,
    key: bytes,
    binding_id: str,
    provider: str,
    repo_key: str,
    ref: str | None = None,
    path: str | None = None,
    query_fingerprint: str = "",
) -> int:
    """校验签名与查询上下文，返回页码；失败只抛固定码，不回显游标内容。"""
    if not isinstance(cursor, str):
        raise _invalid()
    parts = cursor.split(".")
    if len(parts) != 2:
        raise _invalid()
    try:
        body = _b64decode(parts[0])
        signature = _b64decode(parts[1])
    except (binascii.Error, ValueError) as exc:
        raise _invalid() from exc
    if len(signature) != SIGNATURE_BYTES:
        raise _invalid()
    if not hmac.compare_digest(signature, _signature(key, body)):
        raise _invalid()
    try:
        payload = json.loads(body)
    except (ValueError, TypeError) as exc:
        raise _invalid() from exc
    if not isinstance(payload, dict) or payload.get("v") != CURSOR_VERSION:
        raise _invalid()
    expected = {
        "b": binding_id,
        "p": provider,
        "r": repo_key,
        "ref": ref,
        "path": path,
        "qfp": query_fingerprint,
    }
    for field in _CONTEXT_KEYS:
        if payload.get(field) != expected[field]:
            raise _invalid()
    page = payload.get("page")
    if not isinstance(page, int) or isinstance(page, bool) or page < 1:
        raise _invalid()
    return page


__all__ = [
    "CURSOR_VERSION",
    "INVALID_CURSOR_MESSAGE",
    "decode_page_cursor",
    "derive_cursor_key",
    "encode_page_cursor",
    "fingerprint_query",
]
