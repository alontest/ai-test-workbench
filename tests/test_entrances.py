"""6 入口配置。用例名带 TC 编号。"""

from __future__ import annotations

import pytest

from workbench.core.entrances import ENTRANCES, get_entrance

EXPECTED_KEYS = (
    "case-library",
    "regression-list",
    "test-report",
    "bug-analysis",
    "log-triage",
    "sql-analysis",
)


def test_tc051_entrances_has_six_items() -> None:
    assert tuple(item.key for item in ENTRANCES) == EXPECTED_KEYS
    for item in ENTRANCES:
        assert item.name
        assert item.description
        assert item.domain
        assert item.status in {"planned", "live"}
    assert get_entrance("case-library").name == "用例库"


def test_tc056_entrance_status_is_config_driven() -> None:
    assert get_entrance("case-library").status == "live"
    assert {
        item.status for item in ENTRANCES if item.key != "case-library"
    } == {"planned"}
    assert get_entrance("unknown-key") is None
    with pytest.raises(IndexError):
        ENTRANCES[99]
