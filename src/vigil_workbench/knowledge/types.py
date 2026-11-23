"""知识库纯类型与数据载体（无 DB、无文件系统依赖）。"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal


class EntryType(str, Enum):
    TERM = "term"
    ENTITY = "entity"
    STATE = "state"
    RULE = "rule"
    PROCESS = "process"
    API = "api"
    DOMAIN_EVENT = "domain_event"
    OTHER = "other"


PREFIX_TO_TYPE: Mapping[str, EntryType] = {
    "TERM": EntryType.TERM,
    "ENT": EntryType.ENTITY,
    "ST": EntryType.STATE,
    "BR": EntryType.RULE,
    "BP": EntryType.PROCESS,
    "API": EntryType.API,
    "DE": EntryType.DOMAIN_EVENT,
}

_PREFIX_PATTERN = re.compile(r"[A-Za-z]+")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def entry_type_for_code(code: str) -> EntryType:
    """按编号前缀映射类型，不信任条目自带的 ``type``。"""
    match = _PREFIX_PATTERN.match(code)
    if match is None:
        return EntryType.OTHER
    return PREFIX_TO_TYPE.get(match.group(0).upper(), EntryType.OTHER)


def parse_iso8601(value: object) -> datetime | None:
    """解析 ISO 8601 为 UTC naive；缺失或非法返回 ``None``，不推断。"""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def summary_digest(summary: str) -> str:
    """``sha256(归一化摘要)``：去首尾空白 + 连续空白压成一个空格。"""
    normalized = _WHITESPACE_PATTERN.sub(" ", summary).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SkippedEntry:
    index: int
    reason: str
    line: int | None = None
    code: str | None = None


@dataclass(frozen=True)
class BodyDuplicate:
    code: str
    file_name: str


@dataclass(frozen=True)
class ImportReport:
    skipped_entries: tuple[SkippedEntry, ...] = ()
    skipped_truncated: bool = False
    neighbors_truncated: int = 0
    extras_dropped: int = 0
    unmatched_files: tuple[str, ...] = ()
    duplicate_bodies: tuple[BodyDuplicate, ...] = ()


@dataclass(frozen=True)
class ParsedEntry:
    index: int
    code: str
    code_key: str
    type: EntryType
    title: str
    summary: str
    fields: Mapping[str, Any] | None
    tables: tuple[str, ...] | None
    code_paths: tuple[str, ...] | None
    neighbors: tuple[Mapping[str, Any], ...] | None
    extras: Mapping[str, Any] | None
    source_doc: str | None
    anchor: str | None
    freshness_at: datetime | None
    content_digest: str
    body: str | None = None
    body_missing: bool = True
    body_source_file: str | None = None


@dataclass(frozen=True)
class ParsedIndex:
    schema: str
    entries: tuple[ParsedEntry, ...]
    generated_at: datetime | None
    report: ImportReport
    index_meta: Mapping[str, Any]


@dataclass(frozen=True)
class BodyMatch:
    text: str
    file_name: str

    @property
    def missing(self) -> bool:
        return not self.text.strip()


@dataclass(frozen=True)
class BodyMatchResult:
    bodies: Mapping[str, BodyMatch]
    duplicate_bodies: tuple[BodyDuplicate, ...] = ()
    unmatched_files: tuple[str, ...] = ()

    def content_for(self, code: str) -> str | None:
        """返回可注入正文；未匹配或空白正文返回 ``None``（不拿空串冒充）。"""
        match = self.bodies.get(code.casefold())
        if match is None or match.missing:
            return None
        return match.text


@dataclass(frozen=True)
class InjectionEntry:
    """注入组装的输入条目：正文优先，缺失时退回摘要。"""

    kb_id: str
    kb_name: str
    kb_version: int
    code: str
    title: str
    body: str | None
    summary: str
    generated_at: datetime | None = None


@dataclass(frozen=True)
class InjectionItem:
    kb_id: str
    kb_name: str
    kb_version: int
    code: str
    title: str
    source: Literal["body", "summary"]
    content: str
    chars: int


@dataclass(frozen=True)
class RenderedInjection:
    text: str
    injection_block: str
    prompt_chars: int
    injected_chars: int
    total_chars: int
    limit: int
    over_limit: bool
    items: tuple[InjectionItem, ...]


__all__ = [
    "BodyDuplicate",
    "BodyMatch",
    "BodyMatchResult",
    "EntryType",
    "ImportReport",
    "InjectionEntry",
    "InjectionItem",
    "PREFIX_TO_TYPE",
    "ParsedEntry",
    "ParsedIndex",
    "RenderedInjection",
    "SkippedEntry",
    "entry_type_for_code",
    "parse_iso8601",
    "summary_digest",
]
