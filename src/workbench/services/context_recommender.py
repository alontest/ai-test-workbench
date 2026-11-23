"""零 LLM 成本的自动上下文推荐：知识条目打分、1 跳邻居与三路代码路径召回。

本模块只做进程内确定性聚合，不调用 ``AiGateway``，也不发外部请求。
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from sqlalchemy import select

from workbench.db.engine import get_sessionmaker
from workbench.db.models import (
    KnowledgeBase,
    KnowledgeEntry,
    ProjectContext,
    RepoBinding,
    RepoFileReadRecord,
)
from workbench.services.errors import DomainError

DEFAULT_LIMIT = 8
MAX_LIMIT = 50
RECENT_READ_LIMIT = 200

_CODE_PATH_RE = re.compile(
    r"(?<![\w./-])"
    r"(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\."
    r"(?:py|pyi|java|kt|kts|ts|tsx|js|jsx|mjs|cjs|go|rs|rb|php|cs|scala|swift|"
    r"c|cc|cpp|h|hpp|sql|vue|svelte|gradle|xml|ya?ml|json)"
    r"(?![\w])"
)
_WORD_RE = re.compile(r"[a-z0-9_]{2,}", re.IGNORECASE)
_CJK_RUN_RE = re.compile(r"[一-鿿]+")

SCORE_CODE_MENTION = 100
SCORE_TITLE_HIT = 40
SCORE_FIELD_MENTION = 30
SCORE_TERM_OVERLAP = 15
NEIGHBOR_MIN_SCORE = 10


def _clean_text(text: str | None) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        raise DomainError(
            "validation_error",
            "输入文本不能为空。",
            details=[{"field": "text", "message": "不能为空白"}],
        )
    return cleaned


def _clean_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    if not 1 <= int(limit) <= MAX_LIMIT:
        raise DomainError(
            "validation_error",
            "推荐条数必须在 1–50 之间。",
            details=[{"field": "limit", "message": f"must be 1-{MAX_LIMIT}"}],
        )
    return int(limit)


def _mentioned(text_lower: str, token: str | None) -> bool:
    token_lower = (token or "").strip().casefold()
    if not token_lower:
        return False
    pattern = re.compile(
        rf"(?<![a-z0-9_]){re.escape(token_lower)}(?![a-z0-9_])"
    )
    return bool(pattern.search(text_lower))


def _element_mentioned(text_lower: str, element: Any) -> bool:
    value = str(element or "").strip().casefold()
    if not value:
        return False
    return value in text_lower or _mentioned(text_lower, value)


def _terms(value: str | None) -> set[str]:
    """词项：ASCII 词 >= 2 字符 + 中文二元组。"""
    if not value:
        return set()
    terms = set(_WORD_RE.findall(value.casefold()))
    for run in _CJK_RUN_RE.findall(value):
        for index in range(len(run) - 1):
            terms.add(run[index : index + 2])
    return terms


def _title_hit(text_lower: str, title: str | None) -> bool:
    title_lower = (title or "").strip().casefold()
    if not title_lower:
        return False
    if title_lower in text_lower:
        return True
    return any(term in text_lower for term in _terms(title_lower))


def _score_entry(
    entry: KnowledgeEntry,
    text_lower: str,
    text_terms: set[str],
) -> int:
    score = 0
    if _mentioned(text_lower, entry.code) or _mentioned(text_lower, entry.code_key):
        score += SCORE_CODE_MENTION
    if _title_hit(text_lower, entry.title):
        score += SCORE_TITLE_HIT
    for group in (entry.tables, entry.fields, entry.code_paths):
        if any(_element_mentioned(text_lower, item) for item in group or ()):
            score += SCORE_FIELD_MENTION
            break
    entry_terms = _terms(entry.summary) | _terms(entry.body or "")
    if text_terms & entry_terms:
        score += SCORE_TERM_OVERLAP
    return score


def _entry_keys(entry: KnowledgeEntry) -> set[str]:
    return {
        str(entry.code or "").casefold(),
        str(entry.code_key or "").casefold(),
    } - {""}


def _neighbor_codes(neighbors: Sequence[Any] | None) -> list[str]:
    result: list[str] = []
    for item in neighbors or ():
        if isinstance(item, Mapping):
            raw = item.get("code") or item.get("codeKey") or item.get("code_key")
        else:
            raw = item
        cleaned = str(raw or "").strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _kb_entry_payload(
    entry: KnowledgeEntry,
    kb: KnowledgeBase,
    *,
    score: int,
    match_source: str,
    via_code: str | None,
) -> dict[str, Any]:
    return {
        "kbId": kb.kb_id,
        "kbName": kb.name,
        "kbNameKey": kb.name_key,
        "code": entry.code,
        "title": entry.title,
        "type": entry.type,
        "summary": entry.summary,
        "score": score,
        "matchSource": match_source,
        "viaCode": via_code,
        "contentDigest": entry.content_digest,
    }


def _select_kb_entries(
    entries: Sequence[KnowledgeEntry],
    kb_by_id: Mapping[str, KnowledgeBase],
    text_lower: str,
    limit: int,
) -> tuple[
    list[dict[str, Any]],
    list[tuple[KnowledgeEntry, KnowledgeBase, int, str]],
]:
    text_terms = _terms(text_lower)
    direct: list[tuple[KnowledgeEntry, KnowledgeBase, int]] = []
    for entry in entries:
        score = _score_entry(entry, text_lower, text_terms)
        if score > 0:
            direct.append((entry, kb_by_id[entry.kb_id], score))
    direct.sort(key=lambda item: (-item[2], item[0].code.casefold()))

    by_key: dict[str, KnowledgeEntry] = {}
    for entry in entries:
        for key in _entry_keys(entry):
            by_key.setdefault(key, entry)

    direct_codes = {
        key for entry, _kb, _score in direct for key in _entry_keys(entry)
    }
    neighbors: dict[str, tuple[KnowledgeEntry, KnowledgeBase, int, str]] = {}
    for entry, _kb, score in direct:
        for code in _neighbor_codes(entry.neighbors):
            target = by_key.get(code.casefold())
            if target is None:
                continue
            if _entry_keys(target) & direct_codes:
                continue
            candidate = max(NEIGHBOR_MIN_SCORE, score // 2)
            current = neighbors.get(target.entry_id)
            if current is None or candidate > current[2]:
                neighbors[target.entry_id] = (
                    target,
                    kb_by_id[target.kb_id],
                    candidate,
                    entry.code,
                )

    combined: list[tuple[KnowledgeEntry, KnowledgeBase, int, str, str | None]] = [
        (entry, kb, score, "direct", None) for entry, kb, score in direct
    ]
    combined.extend(
        (entry, kb, score, "neighbor_1hop", via_code)
        for entry, kb, score, via_code in neighbors.values()
    )
    combined.sort(
        key=lambda item: (
            0 if item[3] == "direct" else 1,
            -item[2],
            item[0].code.casefold(),
        )
    )
    selected = combined[:limit]
    payloads = [
        _kb_entry_payload(
            entry,
            kb,
            score=score,
            match_source=match_source,
            via_code=via_code,
        )
        for entry, kb, score, match_source, via_code in selected
    ]
    selected_entries = [
        (entry, kb, score, match_source)
        for entry, kb, score, match_source, _via_code in selected
    ]
    return payloads, selected_entries


def _input_path_mentions(text: str) -> list[str]:
    result: list[str] = []
    for match in _CODE_PATH_RE.finditer(text):
        path = match.group(0)
        if path not in result:
            result.append(path)
    return result


def _merge_code_paths(
    *,
    kb_paths: Iterable[tuple[str, str]],
    recent_reads: Iterable[tuple[str, str]],
    input_paths: Iterable[str],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def add(
        path: str,
        *,
        source: str,
        linked_codes: Sequence[str] = (),
        binding_id: str | None = None,
    ) -> None:
        item = merged.get(path)
        if item is None:
            item = {
                "path": path,
                "source": source,
                "linkedKbCodes": [],
                "bindingId": binding_id,
            }
            merged[path] = item
            order.append(path)
        elif source == "kb_code_path":
            item["source"] = "kb_code_path"
        for code in linked_codes:
            if code and code not in item["linkedKbCodes"]:
                item["linkedKbCodes"].append(code)
        if binding_id is not None and item["bindingId"] is None:
            item["bindingId"] = binding_id

    for path, code in kb_paths:
        add(path, source="kb_code_path", linked_codes=[code])
    for path, binding_id in recent_reads:
        add(path, source="recent_repo_read", binding_id=binding_id)
    for path in input_paths:
        add(path, source="input_path_mention")
    return [merged[path] for path in order]


async def _recent_repo_reads(db, project_id: int) -> list[tuple[str, str]]:  # noqa: ANN001
    stmt = (
        select(RepoFileReadRecord)
        .join(RepoBinding, RepoBinding.binding_id == RepoFileReadRecord.binding_id)
        .where(
            RepoBinding.project_id == project_id,
            RepoBinding.active_flag == "1",
            RepoFileReadRecord.status == "success",
        )
        .order_by(
            RepoFileReadRecord.fetched_at.desc(),
            RepoFileReadRecord.read_id.desc(),
        )
        .limit(RECENT_READ_LIMIT)
    )
    rows = list(await db.scalars(stmt))
    return [(row.file_path, row.binding_id) for row in rows]


async def recommend(
    project_id: int,
    *,
    text: str,
    limit: int | None = DEFAULT_LIMIT,
) -> dict[str, Any]:
    """匹配知识条目（含 1 跳邻居）并聚合三路代码路径。"""
    cleaned_text = _clean_text(text)
    cleaned_limit = _clean_limit(limit)
    text_lower = cleaned_text.casefold()

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        project = await db.get(ProjectContext, project_id)
        if project is None:
            raise DomainError(
                "project_not_found",
                "项目不存在。",
                status_code=404,
                details=[{"field": "projectId", "message": "project not found"}],
            )
        kbs = list(
            await db.scalars(
                select(KnowledgeBase).where(
                    KnowledgeBase.project_id == project_id,
                    KnowledgeBase.current_flag == "1",
                )
            )
        )
        kb_by_id = {kb.kb_id: kb for kb in kbs}
        entries: list[KnowledgeEntry] = []
        if kb_by_id:
            entries = list(
                await db.scalars(
                    select(KnowledgeEntry).where(
                        KnowledgeEntry.kb_id.in_(list(kb_by_id))
                    )
                )
            )
        recent_reads = await _recent_repo_reads(db, project_id)

    recommended_kb_entries, selected_entries = _select_kb_entries(
        entries, kb_by_id, text_lower, cleaned_limit
    )

    kb_paths: list[tuple[str, str]] = []
    for entry, _kb, _score, _match_source in selected_entries:
        for path in entry.code_paths or ():
            cleaned_path = str(path or "").strip()
            if cleaned_path:
                kb_paths.append((cleaned_path, entry.code))
    input_paths = _input_path_mentions(cleaned_text)
    recommended_code_paths = _merge_code_paths(
        kb_paths=kb_paths,
        recent_reads=recent_reads,
        input_paths=input_paths,
    )
    return {
        "recommendedKbEntries": recommended_kb_entries,
        "recommendedCodePaths": recommended_code_paths,
    }
