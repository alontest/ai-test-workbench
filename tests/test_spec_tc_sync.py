"""用例名里的 TC 编号必须登记在 spec 的 tc-map.json。

6c4c257 先落地了 TC-071 的用例，tc-map.json 直到下一个提交才补上：
测试全绿，覆盖矩阵却少一条。这里把「新增 TC 必须同提交登记」变成断言，
免得矩阵靠自己记得去改。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SPECS_DIR = TESTS_DIR.parent / "specs"

DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z0-9_]+)\s*\(", re.M)
TC_IN_NAME_RE = re.compile(r"(?i)(?<![A-Za-z])TC[-_]?(\d{1,4})(?!\d)")


def tc_ids_in_source(source: str) -> set[str]:
    """只认函数名里的 TC 编号，和 aw verify 从 JUnit 用例名里读的口径一致。"""
    ids: set[str] = set()
    for name in DEF_RE.findall(source):
        for match in TC_IN_NAME_RE.finditer(name):
            ids.add("TC-" + match.group(1))
    return ids


def collected_tc_ids(tests_dir: Path) -> set[str]:
    ids: set[str] = set()
    for path in tests_dir.rglob("*.py"):
        ids |= tc_ids_in_source(path.read_text(encoding="utf-8"))
    return ids


def registered_tc_ids(tc_map: dict[str, list[str]]) -> set[str]:
    return {tc for tcs in tc_map.values() for tc in tcs}


def unregistered_ids(test_ids: set[str], tc_map: dict[str, list[str]]) -> set[str]:
    return test_ids - registered_tc_ids(tc_map)


def test_guard_every_test_tc_is_registered() -> None:
    maps = sorted(SPECS_DIR.glob("*/test-verification/tc-map.json"))
    assert maps, f"没有找到任何 tc-map.json：{SPECS_DIR}"

    test_ids = collected_tc_ids(TESTS_DIR)
    assert test_ids, "没有从用例名里读到任何 TC 编号"

    registered: set[str] = set()
    for map_path in maps:
        registered |= registered_tc_ids(json.loads(map_path.read_text(encoding="utf-8")))

    missing = sorted(test_ids - registered)
    assert not missing, (
        "这些 TC 在用例里出现了，但没有登记到 tc-map.json：\n"
        + "\n".join(missing)
    )


def test_guard_checker_catches_historical_gap() -> None:
    """检查器必须能抓到 6c4c257 上「用例先落地、矩阵没跟」的状态。"""
    # 拼出来，避免这段历史函数名被本文件的收集当成真的 TC。
    historical_tests = (
        "async " + "def test_tc071_db_error_mapping_is_dialect_portable"
        "(settings, database) -> None:\n    ...\n"
    )
    historical_map = {"TASK-TD-014": ["TC-070"]}
    assert unregistered_ids(tc_ids_in_source(historical_tests), historical_map) == {
        "TC-071"
    }


def test_guard_ignores_tests_without_tc() -> None:
    assert tc_ids_in_source("def helper_without_id() -> None: ...\n") == set()
    assert tc_ids_in_source("async def another_helper() -> None: ...\n") == set()
