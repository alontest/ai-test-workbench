"""日志、异常与响应摘要的统一脱敏。"""

from __future__ import annotations

import logging
import re

REDACTED = "[REDACTED]"
DEFAULT_MAX_LENGTH = 2000

_HEADER_PATTERN = re.compile(
    r"(?im)\b(authorization|cookie|set-cookie|x-api-key)\b\s*[:=]\s*[^\r\n]+"
)
_KV_PATTERN = re.compile(
    r"""(?i)(["']?(?:api[_-]?key|password|passwd|secret|token)["']?\s*[:=]\s*)"""
    r"""("?)([^"'\s,;}]+)"""
)
_BEARER_PATTERN = re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+")
_SK_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{2,}\b")


def redact(text: str, *, max_length: int | None = DEFAULT_MAX_LENGTH) -> str:
    """移除凭据类内容，并按需截断。"""
    if not text:
        return text
    cleaned = _HEADER_PATTERN.sub(lambda m: f"{m.group(1)}: {REDACTED}", text)
    cleaned = _KV_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}{REDACTED}", cleaned)
    cleaned = _BEARER_PATTERN.sub(f"Bearer {REDACTED}", cleaned)
    cleaned = _SK_PATTERN.sub(REDACTED, cleaned)
    if max_length is not None and len(cleaned) > max_length:
        return cleaned[:max_length]
    return cleaned


class RedactionFilter(logging.Filter):
    """把日志记录的消息替换为脱敏后的文本。"""

    def __init__(self, max_length: int | None = DEFAULT_MAX_LENGTH) -> None:
        super().__init__()
        self._max_length = max_length

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - 防御性：格式串异常不阻断日志
            message = str(record.msg)
        record.msg = redact(message, max_length=self._max_length)
        record.args = ()
        return True
