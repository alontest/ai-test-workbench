"""知识库解析层：纯函数、无 DB / 无文件系统依赖。"""

from vigil_workbench.knowledge.body_matcher import match_bodies
from vigil_workbench.knowledge.config import KbSettings, get_kb_settings
from vigil_workbench.knowledge.errors import (
    IndexJsonError,
    KbDomainError,
    KnowledgeInjectionEmptyError,
    KnowledgeInvalidEntriesError,
    PromptBudgetExceededError,
)
from vigil_workbench.knowledge.index_parser import parse_index
from vigil_workbench.knowledge.naming import derive_name, name_key
from vigil_workbench.knowledge.rendering import render_injection
from vigil_workbench.knowledge.types import (
    BodyMatchResult,
    EntryType,
    ImportReport,
    InjectionEntry,
    InjectionItem,
    ParsedEntry,
    ParsedIndex,
    RenderedInjection,
)

__all__ = [
    "BodyMatchResult",
    "EntryType",
    "ImportReport",
    "IndexJsonError",
    "InjectionEntry",
    "InjectionItem",
    "KbDomainError",
    "KbSettings",
    "KnowledgeInjectionEmptyError",
    "KnowledgeInvalidEntriesError",
    "ParsedEntry",
    "ParsedIndex",
    "PromptBudgetExceededError",
    "RenderedInjection",
    "derive_name",
    "get_kb_settings",
    "match_bodies",
    "name_key",
    "parse_index",
    "render_injection",
]
