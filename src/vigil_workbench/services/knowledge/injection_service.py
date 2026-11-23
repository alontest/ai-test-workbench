"""注入组装：候选、只读预览、失效重校验、字符预算与 core 快照。

唯一组装入口（ADR-109）：``preview`` 与 ``prepare_for_call`` 共用同一解析与
渲染路径；``preview`` 不落库、不调模型，超限与失效都不是错误。
错误与日志只含 kbId / 编号 / 计数 / 字符数，绝不回显正文（ADR-114）。
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from vigil_workbench.api.serialization import to_rfc3339
from vigil_workbench.core.ports import (
    InjectionItem as CoreInjectionItem,
    InjectionSnapshot,
    InvalidCodeRef,
    KnowledgeRef,
    PreparedInjection,
)
from vigil_workbench.db.base import utcnow
from vigil_workbench.db.engine import get_sessionmaker
from vigil_workbench.db.models import AnalysisSession, KnowledgeBase, KnowledgeEntry
from vigil_workbench.db.repositories import knowledge as knowledge_repo
from vigil_workbench.db.repositories import knowledge_query
from vigil_workbench.knowledge.config import KbSettings, get_kb_settings
from vigil_workbench.knowledge.errors import (
    KnowledgeInjectionEmptyError,
    KnowledgeInvalidEntriesError,
    PromptBudgetExceededError,
)
from vigil_workbench.knowledge.rendering import render_injection
from vigil_workbench.knowledge.types import InjectionEntry, RenderedInjection
from vigil_workbench.services.errors import DomainError
from vigil_workbench.services.knowledge.query_service import (
    DEFAULT_LIMIT,
    KnowledgeQueryService,
)

logger = logging.getLogger(__name__)

REASON_KB_DELETED = "kb_deleted"
REASON_ENTRY_NOT_FOUND = "entry_not_found"
REASON_SUPERSEDED = "superseded"

ResolvedEntry = tuple[KnowledgeBase, KnowledgeEntry]


def _session_not_found() -> DomainError:
    return DomainError(
        "session_not_found",
        "会话不存在。",
        status_code=404,
        details=[{"field": "sessionId", "message": "会话不存在"}],
    )


def _allocate_shares(raw: Sequence[int], total: int) -> list[int]:
    """把分组字符数调整为恰好等于注入块总长（core 校验 sum(items) == 总长）。"""
    shares = list(raw)
    if not shares:
        return shares
    diff = total - sum(shares)
    if diff > 0:
        shares[0] += diff
        return shares
    remaining = -diff
    index = 0
    while remaining > 0 and index < len(shares):
        taken = min(shares[index], remaining)
        shares[index] -= taken
        remaining -= taken
        index += 1
    return shares


def _injection_entries(valid: Sequence[ResolvedEntry]) -> list[InjectionEntry]:
    return [
        InjectionEntry(
            kb_id=kb.kb_id,
            kb_name=kb.name,
            kb_version=kb.version,
            code=entry.code,
            title=entry.title,
            body=entry.body,
            summary=entry.summary or "",
            generated_at=kb.index_generated_at,
        )
        for kb, entry in valid
    ]


def _render(
    valid: Sequence[ResolvedEntry], user_prompt: str, limit: int
) -> RenderedInjection:
    return render_injection(
        _injection_entries(valid), user_prompt, limit=limit
    )


def _snapshot(
    rendered: RenderedInjection,
    invalid: Sequence[dict[str, object]],
) -> InjectionSnapshot:
    groups: dict[str, dict[str, Any]] = {}
    for item in rendered.items:
        group = groups.setdefault(
            item.kb_id,
            {
                "kb_name": item.kb_name,
                "kb_version": item.kb_version,
                "codes": [],
                "chars": 0,
            },
        )
        group["codes"].append(item.code)
        group["chars"] += item.chars
    shares = _allocate_shares(
        [group["chars"] for group in groups.values()], rendered.injected_chars
    )
    items = tuple(
        CoreInjectionItem(
            kb_id=kb_id,
            kb_name=group["kb_name"],
            kb_version=group["kb_version"],
            entry_codes=tuple(group["codes"]),
            injected_chars=share,
        )
        for (kb_id, group), share in zip(groups.items(), shares, strict=True)
    )
    return InjectionSnapshot(
        items=items,
        prompt_chars=rendered.prompt_chars,
        injected_chars=rendered.injected_chars,
        total_chars=rendered.total_chars,
        excluded_codes=tuple(str(item["code"]) for item in invalid),
    )


class KnowledgeInjectionService:
    """实现 core ``InjectionPreparer``，并提供候选与预览。"""

    def __init__(
        self,
        *,
        sessionmaker=None,  # noqa: ANN001
        kb_settings: KbSettings | None = None,
        settings: Any | None = None,
        now: datetime | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._kb_settings = kb_settings
        self._settings = settings
        self._now = now

    @property
    def sessionmaker(self):  # noqa: ANN201
        return self._sessionmaker or get_sessionmaker()

    @property
    def kb_settings(self) -> KbSettings:
        return self._kb_settings or get_kb_settings()

    @property
    def settings(self):  # noqa: ANN201
        if self._settings is None:
            from vigil_workbench.config import get_settings

            self._settings = get_settings()
        return self._settings

    def _clock(self) -> datetime:
        return self._now or utcnow()

    # --- 候选 ---------------------------------------------------------------

    async def session_project(self, session_id: int) -> int:
        async with self.sessionmaker() as db:
            session = await db.get(AnalysisSession, session_id)
            if session is None:
                raise _session_not_found()
            return session.project_id

    async def candidates(
        self,
        *,
        session_id: int,
        q: str | None = None,
        entry_type: str | None = None,
        limit: int = DEFAULT_LIMIT,
        cursor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        project_id = await self.session_project(session_id)
        page = await KnowledgeQueryService(
            sessionmaker=self.sessionmaker,
            kb_settings=self.kb_settings,
            now=self._now,
        ).search_entries(
            project_id=project_id,
            entry_type=entry_type,
            q=q,
            limit=limit,
            cursor=cursor,
        )
        return {"projectId": project_id, **page}

    # --- 预览 ---------------------------------------------------------------

    async def preview(
        self,
        *,
        project_id: int,
        refs: Sequence[KnowledgeRef],
        user_prompt: str,
    ) -> dict[str, Any]:
        limit = self.settings.prompt_max_chars
        async with self.sessionmaker() as db:
            valid, invalid = await self._resolve(db, project_id, refs)
            rendered = _render(valid, user_prompt, limit)
            warnings = await self._warnings(db, project_id, valid)
        return {
            "items": [
                {
                    "kbId": item.kb_id,
                    "kbName": item.kb_name,
                    "kbVersion": item.kb_version,
                    "code": item.code,
                    "title": item.title,
                    "chars": item.chars,
                    "source": item.source,
                }
                for item in rendered.items
            ],
            "invalidItems": invalid,
            "promptChars": rendered.prompt_chars,
            "injectedChars": rendered.injected_chars,
            "totalChars": rendered.total_chars,
            "limit": limit,
            "overLimit": rendered.over_limit,
            "warnings": warnings,
        }

    # --- core 进程内契约 ----------------------------------------------------

    async def prepare_for_call(
        self,
        *,
        session_id: int,
        project_id: int,
        prompt: str,
        knowledge_refs: Sequence[KnowledgeRef],
        confirm_invalid_codes: Sequence[InvalidCodeRef],
    ) -> PreparedInjection:
        limit = self.settings.prompt_max_chars
        async with self.sessionmaker() as db:
            valid, invalid = await self._resolve(db, project_id, knowledge_refs)

        expected = {(str(item["kbId"]), str(item["code"]).casefold()) for item in invalid}
        confirmed = {
            (str(ref.kb_id), str(ref.code).casefold())
            for ref in confirm_invalid_codes
        }
        if expected != confirmed:
            raise KnowledgeInvalidEntriesError(invalid)
        if not valid:
            raise KnowledgeInjectionEmptyError()

        rendered = _render(valid, prompt, limit)
        if rendered.over_limit:
            raise PromptBudgetExceededError(
                prompt_chars=rendered.prompt_chars,
                injected_chars=rendered.injected_chars,
                total_chars=rendered.total_chars,
                limit=limit,
            )
        snapshot = _snapshot(rendered, invalid)
        logger.info(
            "knowledge injection prepared kb_count=%s entry_count=%s injected_chars=%s",
            len(snapshot.items),
            len(rendered.items),
            snapshot.injected_chars,
        )
        return PreparedInjection(prepared=rendered.text, snapshot=snapshot)

    # --- 解析与提示 ---------------------------------------------------------

    async def _resolve(
        self,
        db: AsyncSession,
        project_id: int,
        refs: Sequence[KnowledgeRef],
    ) -> tuple[list[ResolvedEntry], list[dict[str, object]]]:
        requested: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for ref in refs:
            kb_id = str(ref.kb_id)
            for raw_code in ref.entry_codes:
                code = str(raw_code)
                key = (kb_id, code.casefold())
                if key in seen:
                    continue
                seen.add(key)
                requested.append((kb_id, code))
        requested.sort(key=lambda item: (item[0], item[1].casefold(), item[1]))
        if not requested:
            return [], []

        bases = await knowledge_repo.get_many(
            db, sorted({kb_id for kb_id, _code in requested})
        )
        scopes: dict[str, list[str]] = {}
        for kb_id, code in requested:
            kb = bases.get(kb_id)
            if self._is_current(kb, project_id):
                scopes.setdefault(kb_id, []).append(code.casefold())
        entries = await knowledge_repo.entries_by_codes(db, scopes)

        valid: list[ResolvedEntry] = []
        invalid: list[dict[str, object]] = []
        for kb_id, code in requested:
            kb = bases.get(kb_id)
            if kb is None or kb.project_id != project_id:
                invalid.append(
                    {"kbId": kb_id, "code": code, "reason": REASON_KB_DELETED}
                )
                continue
            if not self._is_current(kb, project_id):
                invalid.append(
                    {"kbId": kb_id, "code": code, "reason": REASON_SUPERSEDED}
                )
                continue
            entry = entries.get((kb_id, code.casefold()))
            if entry is None:
                invalid.append(
                    {"kbId": kb_id, "code": code, "reason": REASON_ENTRY_NOT_FOUND}
                )
                continue
            valid.append((kb, entry))
        return valid, invalid

    @staticmethod
    def _is_current(kb: KnowledgeBase | None, project_id: int) -> bool:
        return (
            kb is not None
            and kb.project_id == project_id
            and kb.status == "ready"
            and kb.current_flag == "1"
        )

    async def _warnings(
        self,
        db: AsyncSession,
        project_id: int,
        valid: Sequence[ResolvedEntry],
    ) -> list[dict[str, object]]:
        if not valid:
            return []
        kb_settings = self.kb_settings
        now = self._clock()
        stale_before = now - timedelta(days=kb_settings.stale_days)
        warnings: list[dict[str, object]] = []
        for kb, entry in valid:
            at = entry.freshness_at
            if at is not None and at < stale_before:
                warnings.append(
                    {
                        "kind": "stale",
                        "kbId": kb.kb_id,
                        "code": entry.code,
                        "detail": f"freshness_at={to_rfc3339(at)}",
                    }
                )

        rows = await knowledge_query.list_conflict_rows(
            db, scopes=[(project_id, entry.code_key) for _kb, entry in valid]
        )
        conflicts: dict[str, list[tuple[str, KnowledgeBase]]] = {}
        for code_key, digest, _project_id, source_kb in rows:
            conflicts.setdefault(code_key, []).append((digest, source_kb))
        for kb, entry in valid:
            emitted = 0
            for digest, source_kb in conflicts.get(entry.code_key, ()):
                if digest == entry.content_digest:
                    continue
                if emitted >= kb_settings.conflict_sources:
                    break
                warnings.append(
                    {
                        "kind": "conflict",
                        "kbId": kb.kb_id,
                        "code": entry.code,
                        "detail": (
                            f"kbId={source_kb.kb_id} version={source_kb.version}"
                        ),
                    }
                )
                emitted += 1
        return warnings


__all__ = [
    "KnowledgeInjectionService",
    "REASON_ENTRY_NOT_FOUND",
    "REASON_KB_DELETED",
    "REASON_SUPERSEDED",
]
