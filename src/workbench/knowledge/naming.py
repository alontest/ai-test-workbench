"""知识库名称推导与 ``name_key``（纯函数，ADR-104）。"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from pathlib import PurePosixPath
from typing import Any

NAME_MAX_CHARS = 200
_FALLBACK_PREFIX = "知识库 "


def name_key(name: str) -> str:
    return name.strip().casefold()


def _parent_directory(path: Any) -> str | None:
    if not isinstance(path, str) or not path.strip():
        return None
    parent = PurePosixPath(path.strip()).parent.name
    if not parent or parent == ".":
        return None
    return parent


def _candidates(
    explicit: str | None, index_meta: Mapping[str, Any], index_sha256: str
) -> Iterator[str]:
    yield explicit or ""
    yield index_meta.get("name") if isinstance(index_meta.get("name"), str) else ""

    meta = index_meta.get("meta")
    meta = meta if isinstance(meta, dict) else {}
    yield meta.get("name") if isinstance(meta.get("name"), str) else ""

    source = meta.get("source")
    source = source if isinstance(source, dict) else {}
    files = source.get("files")
    if isinstance(files, list) and files and isinstance(files[0], dict):
        parent = _parent_directory(files[0].get("path"))
        if parent:
            yield parent

    fingerprint = meta.get("graph_fingerprint") or index_meta.get("graph_fingerprint")
    if isinstance(fingerprint, str) and fingerprint.strip():
        yield f"{_FALLBACK_PREFIX}{fingerprint.strip()[:8]}"

    yield f"{_FALLBACK_PREFIX}{index_sha256[:8]}"


def derive_name(
    explicit: str | None, index_meta: Mapping[str, Any], index_sha256: str
) -> str:
    """按六级顺序推导名称，trim 后 ≤200。"""
    for candidate in _candidates(explicit, index_meta, index_sha256):
        cleaned = candidate.strip()
        if cleaned:
            return cleaned[:NAME_MAX_CHARS]
    # ``_candidates`` 最后一项是 sha256 前缀，正常情况下不会走到这里。
    return f"{_FALLBACK_PREFIX}{index_sha256[:8]}"


__all__ = ["NAME_MAX_CHARS", "derive_name", "name_key"]
