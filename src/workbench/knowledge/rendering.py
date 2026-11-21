"""注入块模板与 Unicode 码点字符预算（纯函数，ADR-109）。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Literal

from workbench.knowledge.types import InjectionEntry, InjectionItem, RenderedInjection

HEADER = "【知识库上下文】"
KB_LINE_TEMPLATE = "知识库：{name} v{version}（生成时间：{generated_at}）"
ENTRY_HEADING_TEMPLATE = "### {code} {title}"
UNKNOWN_GENERATED_AT = "未知"
MISSING_BODY_SUFFIX = "（正文缺失）"
BLOCK_TRAILER = "\n\n"


def _format_generated_at(value: datetime | None) -> str:
    if value is None:
        return UNKNOWN_GENERATED_AT
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat()


def _content(entry: InjectionEntry) -> tuple[Literal["body", "summary"], str]:
    """返回 ``(source, 可注入文本)``；正文缺失时用摘要并标注。"""
    body = (entry.body or "").strip()
    if body:
        return "body", body
    summary = (entry.summary or "").strip()
    return "summary", f"{summary}{MISSING_BODY_SUFFIX}"


def _group(entries: Sequence[InjectionEntry]) -> list[list[InjectionEntry]]:
    groups: dict[str, list[InjectionEntry]] = {}
    for entry in entries:
        groups.setdefault(entry.kb_id, []).append(entry)
    return list(groups.values())


def render_injection(
    entries: Sequence[InjectionEntry], user_prompt: str, *, limit: int
) -> RenderedInjection:
    """固定模板组装注入块；``text == injection_block + user_prompt``。"""
    lines: list[str] = [HEADER]
    items: list[InjectionItem] = []
    for group in _group(entries):
        head = group[0]
        lines.append(
            KB_LINE_TEMPLATE.format(
                name=head.kb_name,
                version=head.kb_version,
                generated_at=_format_generated_at(head.generated_at),
            )
        )
        for entry in group:
            source, content = _content(entry)
            heading = ENTRY_HEADING_TEMPLATE.format(code=entry.code, title=entry.title)
            lines.append(heading)
            lines.append(content)
            items.append(
                InjectionItem(
                    kb_id=entry.kb_id,
                    kb_name=entry.kb_name,
                    kb_version=entry.kb_version,
                    code=entry.code,
                    title=entry.title,
                    source=source,
                    content=content,
                    chars=len(f"{heading}\n{content}{BLOCK_TRAILER}"),
                )
            )

    injection_block = "\n".join(lines) + BLOCK_TRAILER
    text = injection_block + user_prompt
    total_chars = len(text)
    return RenderedInjection(
        text=text,
        injection_block=injection_block,
        prompt_chars=len(user_prompt),
        injected_chars=len(injection_block),
        total_chars=total_chars,
        limit=limit,
        over_limit=total_chars > limit,
        items=tuple(items),
    )


__all__ = [
    "HEADER",
    "KB_LINE_TEMPLATE",
    "MISSING_BODY_SUFFIX",
    "UNKNOWN_GENERATED_AT",
    "render_injection",
]
