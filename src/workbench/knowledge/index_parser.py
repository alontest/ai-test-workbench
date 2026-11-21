"""``index.json`` 解析器与资源护栏（纯函数，无 DB / 无文件系统）。"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from workbench.knowledge.config import KbSettings
from workbench.knowledge.errors import IndexJsonError
from workbench.knowledge.types import (
    ImportReport,
    ParsedEntry,
    ParsedIndex,
    SkippedEntry,
    entry_type_for_code,
    parse_iso8601,
    summary_digest,
)

ID_PATTERN = re.compile(r"^[\w一-鿿][\w一-鿿.\-]{0,127}$", re.UNICODE)
_ID_LINE_TEMPLATE = r'"id"\s*:\s*"{}"'

REASON_INVALID_ENTRY = "invalid_entry"
REASON_INVALID_ID = "invalid_id"
REASON_DUPLICATE_CODE = "duplicate_code"
REASON_INVALID_FIELDS = "invalid_fields"
REASON_INVALID_TABLES = "invalid_tables"
REASON_INVALID_CODE_PATHS = "invalid_code_paths"

REASON_INVALID_UTF8 = "invalid_utf8"
REASON_INVALID_JSON = "invalid_json"
REASON_JSON_TOO_DEEP = "json_too_deep"
REASON_INVALID_TOP_LEVEL = "invalid_top_level"
REASON_INVALID_SCHEMA = "invalid_schema"
REASON_INVALID_ENTRIES = "invalid_entries"
REASON_TOO_MANY_ENTRIES = "too_many_entries"
REASON_NO_ENTRIES_IMPORTABLE = "no_entries_importable"

_MODELED_KEYS = frozenset(
    {
        "id",
        "zh_name",
        "name",
        "zh_definition",
        "description",
        "content",
        "fields",
        "tables",
        "code_paths",
        "neighbors",
        "source_doc",
        "anchor",
        "freshness_at",
        "updated_at",
    }
)
_TITLE_KEYS = ("zh_name", "name")
_SUMMARY_KEYS = ("zh_definition", "description", "content")


class _LineLocator:
    """尽力定位 ``"id": "<code>"`` 的行号；重复编号按出现顺序推进。"""

    def __init__(self, text: str) -> None:
        self._text = text
        self._offsets: dict[str, int] = {}

    def locate(self, code: str) -> int | None:
        pattern = re.compile(_ID_LINE_TEMPLATE.format(re.escape(code)))
        start = self._offsets.get(code, 0)
        match = pattern.search(self._text, start)
        if match is None and start > 0:
            match = pattern.search(self._text)
        if match is None:
            return None
        self._offsets[code] = match.end()
        return self._text.count("\n", 0, match.start()) + 1


def _reject_constant(value: str) -> None:
    raise ValueError(f"unsupported constant: {value}")


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IndexJsonError(REASON_INVALID_UTF8) from exc


def _load_json(text: str) -> Any:
    try:
        return json.loads(text, parse_constant=_reject_constant)
    except json.JSONDecodeError as exc:
        raise IndexJsonError(
            REASON_INVALID_JSON, line=exc.lineno, column=exc.colno
        ) from exc
    except RecursionError as exc:
        raise IndexJsonError(REASON_JSON_TOO_DEEP) from exc
    except ValueError as exc:
        raise IndexJsonError(REASON_INVALID_JSON) from exc


def _json_depth(value: Any) -> int:
    max_depth = 0
    stack: list[tuple[Any, int]] = [(value, 1)]
    while stack:
        node, depth = stack.pop()
        max_depth = max(max_depth, depth)
        if isinstance(node, dict):
            stack.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            stack.extend((child, depth + 1) for child in node)
    return max_depth


def _enforce_depth(document: Any, settings: KbSettings) -> None:
    depth = _json_depth(document)
    if depth > settings.max_json_depth:
        raise IndexJsonError(
            REASON_JSON_TOO_DEEP, count=depth, limit=settings.max_json_depth
        )


def _first_text(
    entry: Mapping[str, Any], keys: tuple[str, ...], *, strip: bool
) -> str | None:
    for key in keys:
        value = entry.get(key)
        if not isinstance(value, str):
            continue
        text = value.strip() if strip else value
        if text.strip():
            return text
    return None


def _string_list(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def _neighbors(value: Any, settings: KbSettings) -> tuple[tuple[dict[str, Any], ...] | None, bool]:
    if not isinstance(value, list):
        return None, False
    kept = [item for item in value if isinstance(item, dict)]
    truncated = len(kept) > settings.max_neighbors
    if truncated:
        kept = kept[: settings.max_neighbors]
    return tuple(kept), truncated


def _extras(entry: Mapping[str, Any], settings: KbSettings) -> tuple[dict[str, Any] | None, bool]:
    extra = {key: value for key, value in entry.items() if key not in _MODELED_KEYS}
    if not extra:
        return None, False
    canonical = json.dumps(
        extra, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    if len(canonical.encode("utf-8")) > settings.max_extras_bytes:
        return None, True
    return extra, False


def _generated_at(document: Mapping[str, Any]) -> datetime | None:
    meta = document.get("meta")
    if isinstance(meta, dict):
        source = meta.get("source")
        if isinstance(source, dict):
            parsed = parse_iso8601(source.get("exported_at"))
            if parsed is not None:
                return parsed
            if source.get("exported_at") is not None:
                return None
    return parse_iso8601(document.get("generated_at"))


def _index_meta(document: Mapping[str, Any]) -> Mapping[str, Any]:
    meta = document.get("meta")
    return {
        "name": document.get("name"),
        "graph_fingerprint": document.get("graph_fingerprint"),
        "meta": meta if isinstance(meta, dict) else {},
    }


def _freshness(entry: Mapping[str, Any]) -> datetime | None:
    value = entry.get("freshness_at")
    if value is None:
        value = entry.get("updated_at")
    return parse_iso8601(value)


def _parse_entry(
    raw: Any,
    index: int,
    locator: _LineLocator,
    settings: KbSettings,
    seen: dict[str, str],
) -> tuple[ParsedEntry | None, SkippedEntry | None, bool, bool]:
    """返回 ``(条目, 跳过项, neighbors 截断, extras 丢弃)``。"""
    if not isinstance(raw, dict):
        return None, SkippedEntry(index=index, reason=REASON_INVALID_ENTRY), False, False

    code = raw.get("id")
    if not isinstance(code, str) or not ID_PATTERN.match(code):
        line = locator.locate(code) if isinstance(code, str) else None
        return (
            None,
            SkippedEntry(
                index=index,
                reason=REASON_INVALID_ID,
                line=line,
                code=code if isinstance(code, str) else None,
            ),
            False,
            False,
        )

    line = locator.locate(code)
    code_key = code.casefold()
    if code_key in seen:
        return (
            None,
            SkippedEntry(
                index=index, reason=REASON_DUPLICATE_CODE, line=line, code=code
            ),
            False,
            False,
        )

    fields = raw.get("fields")
    if fields is not None and not isinstance(fields, dict):
        return None, SkippedEntry(index, REASON_INVALID_FIELDS, line, code), False, False

    tables = None
    if raw.get("tables") is not None:
        tables = _string_list(raw.get("tables"))
        if tables is None:
            return None, SkippedEntry(index, REASON_INVALID_TABLES, line, code), False, False

    code_paths = None
    if raw.get("code_paths") is not None:
        code_paths = _string_list(raw.get("code_paths"))
        if code_paths is None:
            return (
                None,
                SkippedEntry(index, REASON_INVALID_CODE_PATHS, line, code),
                False,
                False,
            )

    neighbors, neighbors_truncated = _neighbors(raw.get("neighbors"), settings)
    extras, extras_dropped = _extras(raw, settings)
    title = _first_text(raw, _TITLE_KEYS, strip=True) or code
    summary = _first_text(raw, _SUMMARY_KEYS, strip=False) or ""

    seen[code_key] = code
    parsed = ParsedEntry(
        index=index,
        code=code,
        code_key=code_key,
        type=entry_type_for_code(code),
        title=title,
        summary=summary,
        fields=fields,
        tables=tables,
        code_paths=code_paths,
        neighbors=neighbors,
        extras=extras,
        source_doc=raw.get("source_doc") if isinstance(raw.get("source_doc"), str) else None,
        anchor=raw.get("anchor") if isinstance(raw.get("anchor"), str) else None,
        freshness_at=_freshness(raw),
        content_digest=summary_digest(summary),
    )
    return parsed, None, neighbors_truncated, extras_dropped


def parse_index(raw: bytes, *, settings: KbSettings) -> ParsedIndex:
    """解析 ``index.json``：结构校验、前缀映射、条目级跳过与护栏。"""
    text = _decode(raw)
    document = _load_json(text)
    _enforce_depth(document, settings)

    if not isinstance(document, dict):
        raise IndexJsonError(REASON_INVALID_TOP_LEVEL)
    schema = document.get("schema")
    if not isinstance(schema, str) or not schema.strip():
        raise IndexJsonError(REASON_INVALID_SCHEMA)
    entries = document.get("entries")
    if not isinstance(entries, list) or not entries:
        raise IndexJsonError(REASON_INVALID_ENTRIES)
    if len(entries) > settings.max_entries:
        raise IndexJsonError(
            REASON_TOO_MANY_ENTRIES, count=len(entries), limit=settings.max_entries
        )

    locator = _LineLocator(text)
    seen: dict[str, str] = {}
    parsed_entries: list[ParsedEntry] = []
    skipped: list[SkippedEntry] = []
    neighbors_truncated = 0
    extras_dropped = 0
    for index, raw_entry in enumerate(entries):
        parsed, skip, truncated, dropped = _parse_entry(
            raw_entry, index, locator, settings, seen
        )
        if parsed is not None:
            parsed_entries.append(parsed)
        if skip is not None:
            skipped.append(skip)
        neighbors_truncated += int(truncated)
        extras_dropped += int(dropped)

    if not parsed_entries:
        raise IndexJsonError(
            REASON_NO_ENTRIES_IMPORTABLE, count=len(skipped), limit=len(entries)
        )

    limit = settings.report_max_items
    report = ImportReport(
        skipped_entries=tuple(skipped[:limit]),
        skipped_truncated=len(skipped) > limit,
        neighbors_truncated=neighbors_truncated,
        extras_dropped=extras_dropped,
        duplicate_bodies=(),
        unmatched_files=(),
    )
    return ParsedIndex(
        schema=schema,
        entries=tuple(parsed_entries),
        generated_at=_generated_at(document),
        report=report,
        index_meta=_index_meta(document),
    )


__all__ = ["ID_PATTERN", "parse_index"]
