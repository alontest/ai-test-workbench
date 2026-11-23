"""index.json 解析器与护栏。用例名带 TC 编号。"""

from __future__ import annotations

import json

import pytest

from vigil_workbench.knowledge.config import KbSettings
from vigil_workbench.knowledge.errors import IndexJsonError
from vigil_workbench.knowledge.index_parser import parse_index
from vigil_workbench.knowledge.types import EntryType


def _raw(document: object) -> bytes:
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")


def _settings(**overrides: int) -> KbSettings:
    return KbSettings(_env_file=None, **overrides)


def test_tc101_rejects_index_without_schema_or_entries() -> None:
    cases = (
        {},
        {"schema": "", "entries": [{"id": "ENT-1"}]},
        {"schema": "v1"},
        {"schema": "v1", "entries": []},
        {"schema": "v1", "entries": {"id": "ENT-1"}},
        ["not", "an", "object"],
    )
    for document in cases:
        with pytest.raises(IndexJsonError) as err:
            parse_index(_raw(document), settings=_settings())
        assert err.value.code == "index_json_invalid"


def test_tc102_maps_prefix_to_entry_type() -> None:
    entries = [
        {"id": "TERM-1"},
        {"id": "ENT-1"},
        {"id": "ST-1"},
        {"id": "BR-1"},
        {"id": "BP-1"},
        {"id": "API-1"},
        {"id": "DE-1"},
        {"id": "MOD-1"},
        {"id": "ENT-2", "type": "rule"},
        {"id": "自定义-1"},
    ]
    parsed = parse_index(
        _raw({"schema": "v1", "entries": entries}), settings=_settings()
    )
    assert [entry.type for entry in parsed.entries] == [
        EntryType.TERM,
        EntryType.ENTITY,
        EntryType.STATE,
        EntryType.RULE,
        EntryType.PROCESS,
        EntryType.API,
        EntryType.DOMAIN_EVENT,
        EntryType.OTHER,
        EntryType.ENTITY,
        EntryType.OTHER,
    ]


def test_tc103_skips_invalid_entries_with_line_and_reason() -> None:
    entries = [
        {"id": "ENT-1", "zh_name": "订单"},
        {"name": "没有编号"},
        {"id": "ENT-1", "zh_name": "重复编号"},
        {"id": "ENT-2", "fields": []},
        {"id": "ENT-3", "tables": "orders"},
        {"id": "ENT-4", "code_paths": [1]},
    ]
    parsed = parse_index(
        _raw({"schema": "v1", "entries": entries}), settings=_settings()
    )
    assert [entry.code for entry in parsed.entries] == ["ENT-1"]
    skipped = parsed.report.skipped_entries
    assert [item.reason for item in skipped] == [
        "invalid_id",
        "duplicate_code",
        "invalid_fields",
        "invalid_tables",
        "invalid_code_paths",
    ]
    assert [item.index for item in skipped] == [1, 2, 3, 4, 5]
    assert skipped[0].line is None
    assert skipped[1].line is not None
    assert skipped[1].code == "ENT-1"


def test_tc104_fails_when_no_entry_importable() -> None:
    entries = [{"name": "没有编号"}, {"id": "bad id"}]
    with pytest.raises(IndexJsonError) as err:
        parse_index(_raw({"schema": "v1", "entries": entries}), settings=_settings())
    assert err.value.code == "index_json_invalid"
    assert err.value.reason == "no_entries_importable"


def test_tc105_enforces_parser_guards() -> None:
    with pytest.raises(IndexJsonError) as too_deep:
        node: object = "leaf"
        for _ in range(32):
            node = {"x": node}
        parse_index(
            _raw({"schema": "v1", "entries": [{"id": "ENT-1"}], "deep": node}),
            settings=_settings(max_json_depth=32),
        )
    assert too_deep.value.reason == "json_too_deep"
    assert too_deep.value.limit == 32

    for constant in ("NaN", "Infinity", "-Infinity"):
        raw = (
            '{"schema": "v1", "entries": [{"id": "ENT-1", '
            f'"fields": {{"x": {constant}}}}}]}}'
        ).encode("utf-8")
        with pytest.raises(IndexJsonError) as invalid:
            parse_index(raw, settings=_settings())
        assert invalid.value.code == "index_json_invalid"

    with pytest.raises(IndexJsonError) as recursion:
        parse_index(b"[" * 10_000 + b"]" * 10_000, settings=_settings())
    assert recursion.value.reason == "json_too_deep"

    entries = [{"id": f"ENT-{index}"} for index in range(3)]
    with pytest.raises(IndexJsonError) as too_many:
        parse_index(
            _raw({"schema": "v1", "entries": entries}),
            settings=_settings(max_entries=2),
        )
    assert too_many.value.reason == "too_many_entries"
    assert too_many.value.count == 3
    assert too_many.value.limit == 2


def test_tc106_truncates_neighbors_and_drops_large_extras() -> None:
    neighbors = [{"id": f"ENT-{index}", "relation": "depends_on"} for index in range(250)]
    entries = [
        {
            "id": "ENT-1",
            "neighbors": neighbors,
            "extra": "x" * 70_000,
        }
    ]
    parsed = parse_index(
        _raw({"schema": "v1", "entries": entries}), settings=_settings()
    )
    entry = parsed.entries[0]
    assert entry.neighbors is not None
    assert len(entry.neighbors) == 200
    assert parsed.report.neighbors_truncated == 1
    assert entry.extras is None
    assert parsed.report.extras_dropped == 1


def test_tc107_rejects_invalid_json_syntax() -> None:
    raw = b'{\n  "schema": "v1",\n  "entries": [}\n'
    with pytest.raises(IndexJsonError) as err:
        parse_index(raw, settings=_settings())
    assert err.value.code == "index_json_invalid"
    assert err.value.reason == "invalid_json"
    assert err.value.line is not None
    assert err.value.column is not None
