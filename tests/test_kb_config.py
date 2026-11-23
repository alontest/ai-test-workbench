"""知识库配置契约。用例名带 TC 编号。"""

from __future__ import annotations

import pytest

from vigil_workbench.config import get_settings
from vigil_workbench.knowledge.config import (
    DEFAULT_CONFLICT_SOURCES,
    DEFAULT_MAX_ENTRIES,
    DEFAULT_MAX_EXTRAS_BYTES,
    DEFAULT_MAX_FILES,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_INDEX_BYTES,
    DEFAULT_MAX_JSON_DEPTH,
    DEFAULT_MAX_NEIGHBORS,
    DEFAULT_MAX_TOTAL_BYTES,
    DEFAULT_REPORT_MAX_ITEMS,
    DEFAULT_STALE_DAYS,
    KbSettings,
    get_kb_settings,
)

ENV_NAMES = (
    "VIGIL_KB_MAX_INDEX_BYTES",
    "VIGIL_KB_MAX_FILE_BYTES",
    "VIGIL_KB_MAX_FILES",
    "VIGIL_KB_MAX_TOTAL_BYTES",
    "VIGIL_KB_MAX_ENTRIES",
    "VIGIL_KB_MAX_JSON_DEPTH",
    "VIGIL_KB_MAX_NEIGHBORS",
    "VIGIL_KB_MAX_EXTRAS_BYTES",
    "VIGIL_KB_STALE_DAYS",
    "VIGIL_KB_CONFLICT_SOURCES",
    "VIGIL_KB_REPORT_MAX_ITEMS",
)


def test_tc146_kb_settings_defaults_and_overrides(settings, monkeypatch) -> None:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_kb_settings.cache_clear()
    try:
        kb = get_kb_settings()
        assert kb.max_index_bytes == DEFAULT_MAX_INDEX_BYTES == 20 * 1024 * 1024
        assert kb.max_file_bytes == DEFAULT_MAX_FILE_BYTES == 10 * 1024 * 1024
        assert kb.max_files == DEFAULT_MAX_FILES == 50
        assert kb.max_total_bytes == DEFAULT_MAX_TOTAL_BYTES == 100 * 1024 * 1024
        assert kb.max_entries == DEFAULT_MAX_ENTRIES == 20_000
        assert kb.max_json_depth == DEFAULT_MAX_JSON_DEPTH == 32
        assert kb.max_neighbors == DEFAULT_MAX_NEIGHBORS == 200
        assert kb.max_extras_bytes == DEFAULT_MAX_EXTRAS_BYTES == 65_536
        assert kb.stale_days == DEFAULT_STALE_DAYS == 30
        assert kb.conflict_sources == DEFAULT_CONFLICT_SOURCES == 20
        assert kb.report_max_items == DEFAULT_REPORT_MAX_ITEMS == 200

        # VIGIL_PROMPT_MAX_CHARS 只来自 core settings，不在本 spec 重复定义。
        assert not hasattr(kb, "prompt_max_chars")
        monkeypatch.setenv("VIGIL_PROMPT_MAX_CHARS", "1234")
        get_settings.cache_clear()
        assert get_settings().prompt_max_chars == 1234

        monkeypatch.setenv("VIGIL_KB_MAX_FILES", "3")
        monkeypatch.setenv("VIGIL_KB_STALE_DAYS", "7")
        get_kb_settings.cache_clear()
        overridden = get_kb_settings()
        assert overridden.max_files == 3
        assert overridden.stale_days == 7

        with pytest.raises(ValueError):
            KbSettings(_env_file=None, max_files=0)
    finally:
        get_kb_settings.cache_clear()
        get_settings.cache_clear()
