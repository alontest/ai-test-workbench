"""``.md`` 正文匹配：文件名优先，``### CODE`` 切块兜底（纯函数）。"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from pathlib import PurePosixPath

from workbench.knowledge.types import BodyDuplicate, BodyMatch, BodyMatchResult

HEADING_PATTERN = re.compile(r"^### (\S+)\s*$")
SECTION_BREAK_PATTERN = re.compile(r"^## ")


def _decode(raw: bytes) -> str:
    # 正文是展示性内容，非 UTF-8 字节替换而不是整包失败。
    return raw.decode("utf-8", errors="replace")


def _heading_blocks(text: str) -> Iterator[tuple[str, int, str]]:
    """产出 ``(code_key, 正文起始偏移, 区块文本)``。"""
    current_key: str | None = None
    current_offset = 0
    buffer: list[str] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\r\n")
        heading = HEADING_PATTERN.match(stripped)
        if heading is not None:
            if current_key is not None:
                yield current_key, current_offset, "".join(buffer)
            current_key = heading.group(1).casefold()
            current_offset = offset + len(line)
            buffer = []
        elif current_key is not None and SECTION_BREAK_PATTERN.match(stripped):
            yield current_key, current_offset, "".join(buffer)
            current_key = None
            buffer = []
        elif current_key is not None:
            buffer.append(line)
        offset += len(line)
    if current_key is not None:
        yield current_key, current_offset, "".join(buffer)


def _stem(file_name: str) -> str:
    return PurePosixPath(file_name).stem.casefold()


def match_bodies(
    codes: Sequence[str], files: Sequence[tuple[str, bytes]]
) -> BodyMatchResult:
    """把正文匹配到编号；同一编号多处命中取「文件名升序 + 偏移最小」。"""
    code_by_key = {code.casefold(): code for code in codes}
    candidates: dict[str, list[tuple[str, int, str]]] = {}
    matched_files: set[str] = set()

    for file_name, raw in files:
        text = _decode(raw)
        stem_key = _stem(file_name)
        if stem_key in code_by_key:
            candidates.setdefault(stem_key, []).append((file_name, 0, text.strip()))
            matched_files.add(file_name)
            continue
        for code_key, offset, block in _heading_blocks(text):
            if code_key not in code_by_key:
                continue
            candidates.setdefault(code_key, []).append(
                (file_name, offset, block.strip())
            )
            matched_files.add(file_name)

    bodies: dict[str, BodyMatch] = {}
    duplicates: list[BodyDuplicate] = []
    for code_key, hits in candidates.items():
        hits.sort(key=lambda hit: (hit[0], hit[1]))
        winner_name, _offset, winner_text = hits[0]
        bodies[code_key] = BodyMatch(text=winner_text, file_name=winner_name)
        for extra_name, _extra_offset, _extra_text in hits[1:]:
            duplicates.append(
                BodyDuplicate(code=code_by_key[code_key], file_name=extra_name)
            )

    unmatched = tuple(
        file_name for file_name, _raw in files if file_name not in matched_files
    )
    return BodyMatchResult(
        bodies=bodies,
        duplicate_bodies=tuple(duplicates),
        unmatched_files=unmatched,
    )


__all__ = ["HEADING_PATTERN", "match_bodies"]
