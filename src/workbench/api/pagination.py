"""base64url 游标编解码。"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from workbench.api.errors import ApiError


def encode_cursor(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> dict[str, Any]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
    except (ValueError, TypeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise ApiError(400, "validation_error", "游标非法。", [{"field": "cursor", "message": "invalid cursor"}]) from exc
    if not isinstance(value, dict):
        raise ApiError(400, "validation_error", "游标非法。", [{"field": "cursor", "message": "invalid cursor"}])
    return value
