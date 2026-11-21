"""``AW_KB_*`` 限额与单例。

``AW_PROMPT_MAX_CHARS`` 不在本模块定义：字符预算统一读
``workbench.config.get_settings().prompt_max_chars``，与网关保持同源。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

MIB = 1024 * 1024
DEFAULT_MAX_INDEX_BYTES = 20 * MIB
DEFAULT_MAX_FILE_BYTES = 10 * MIB
DEFAULT_MAX_FILES = 50
DEFAULT_MAX_TOTAL_BYTES = 100 * MIB
DEFAULT_MAX_ENTRIES = 20_000
DEFAULT_MAX_JSON_DEPTH = 32
DEFAULT_MAX_NEIGHBORS = 200
DEFAULT_MAX_EXTRAS_BYTES = 65_536
DEFAULT_STALE_DAYS = 30
DEFAULT_CONFLICT_SOURCES = 20
DEFAULT_REPORT_MAX_ITEMS = 200


class KbSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AW_KB_",
        case_sensitive=False,
        extra="ignore",
    )

    max_index_bytes: int = DEFAULT_MAX_INDEX_BYTES
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_files: int = DEFAULT_MAX_FILES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_entries: int = DEFAULT_MAX_ENTRIES
    max_json_depth: int = DEFAULT_MAX_JSON_DEPTH
    max_neighbors: int = DEFAULT_MAX_NEIGHBORS
    max_extras_bytes: int = DEFAULT_MAX_EXTRAS_BYTES
    stale_days: int = DEFAULT_STALE_DAYS
    conflict_sources: int = DEFAULT_CONFLICT_SOURCES
    report_max_items: int = DEFAULT_REPORT_MAX_ITEMS

    @field_validator("*")
    @classmethod
    def _positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("AW_KB_* 限额必须大于 0")
        return value


@lru_cache(maxsize=1)
def get_kb_settings() -> KbSettings:
    return KbSettings()
