"""跨 spec 端口：knowledge-base 实现 InjectionPreparer 并注册。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class InjectionItem:
    kb_id: str
    kb_name: str
    kb_version: int
    entry_codes: tuple[str, ...]
    injected_chars: int


@dataclass(frozen=True)
class InjectionSnapshot:
    items: tuple[InjectionItem, ...]
    prompt_chars: int
    injected_chars: int
    total_chars: int
    excluded_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class KnowledgeRef:
    kb_id: str
    entry_codes: tuple[str, ...]


@dataclass(frozen=True)
class InvalidCodeRef:
    kb_id: str
    code: str


@dataclass(frozen=True)
class PreparedInjection:
    prepared: str
    snapshot: InjectionSnapshot


class InjectionPreparer(Protocol):
    async def prepare_for_call(
        self,
        *,
        session_id: int,
        project_id: int,
        prompt: str,
        knowledge_refs: Sequence[KnowledgeRef],
        confirm_invalid_codes: Sequence[InvalidCodeRef],
    ) -> PreparedInjection: ...


_preparer: InjectionPreparer | None = None


def register_injection_preparer(impl: InjectionPreparer | None) -> None:
    global _preparer
    _preparer = impl


def get_injection_preparer() -> InjectionPreparer | None:
    return _preparer
