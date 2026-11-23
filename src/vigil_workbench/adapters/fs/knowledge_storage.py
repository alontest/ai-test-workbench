"""知识库文件存储：暂存、服务端命名、包含校验、原子 rename、trash 与孤儿扫描。

客户端文件名只用于展示与正文匹配，绝不拼进磁盘路径（ADR-105 / ADR-114）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STAGING_DIR_NAME = ".staging"
DOCS_DIR_NAME = "docs"
INDEX_FILE_NAME = "index.json"
MANIFEST_FILE_NAME = "manifest.json"
SLUG_MAX_CHARS = 80
HASH_PREFIX_CHARS = 16
WRITE_CHUNK_BYTES = 1024 * 1024
KB_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_TOKEN_PATTERN = re.compile(r"^[0-9a-f]{32}$")
_PATH_SEPARATORS = {"/", "\\"}


class KnowledgePathError(ValueError):
    """目标路径越出 ``knowledge-bases/`` 根或标识非法。"""


def slugify(original_name: str) -> str:
    """取基名并去掉路径分隔符、控制字符与首尾点，长度 ≤80。"""
    base = original_name.replace("\\", "/").rsplit("/", 1)[-1]
    cleaned = "".join(
        char
        for char in base
        if char.isprintable() and char not in _PATH_SEPARATORS
    )
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "file"
    return cleaned[:SLUG_MAX_CHARS]


def stored_name(sha256_hex: str, original_name: str) -> str:
    """服务端落盘名：``sha256[:16]__slug(原名)``。"""
    return f"{sha256_hex[:HASH_PREFIX_CHARS]}__{slugify(original_name)}"


@dataclass(frozen=True)
class StoredFile:
    original_name: str
    storage_name: str
    relative_path: str
    sha256: str
    size: int
    is_index: bool


class KbStorage:
    """``$VIGIL_DATA_DIR/knowledge-bases/`` 下的文件操作。"""

    def __init__(
        self,
        *,
        root: Path | None = None,
        trash_root: Path | None = None,
    ) -> None:
        if root is None:
            from vigil_workbench.config import get_settings

            data_path = get_settings().data_path
            root = data_path / "knowledge-bases"
            trash_root = trash_root or data_path / ".trash"
        self.root = Path(root).expanduser()
        self.trash_root = (
            Path(trash_root) if trash_root is not None else self.root.parent / ".trash"
        )

    # --- 路径 ---------------------------------------------------------------

    def resolve_within(self, relative: str) -> Path:
        """解析相对路径并校验仍在根内；越界抛 ``KnowledgePathError``。"""
        root = self.root.resolve()
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root):
            raise KnowledgePathError("knowledge storage path escapes root")
        return candidate

    def new_token(self) -> str:
        return uuid.uuid4().hex

    def staging_dir(self, token: str) -> Path:
        if not _TOKEN_PATTERN.match(token):
            raise KnowledgePathError("invalid staging token")
        return self.resolve_within(f"{STAGING_DIR_NAME}/{token}")

    def target_dir(self, kb_id: str) -> Path:
        if not KB_ID_PATTERN.match(kb_id):
            raise KnowledgePathError("invalid kb id")
        return self.resolve_within(kb_id)

    def _child(self, directory: Path, name: str) -> Path:
        base = directory.resolve()
        candidate = (base / name).resolve()
        if not candidate.is_relative_to(base) or candidate == base:
            raise KnowledgePathError("knowledge storage path escapes directory")
        return candidate

    # --- 写入与提升 ---------------------------------------------------------

    def stage(
        self, token: str, files: Sequence[tuple[str, bytes]]
    ) -> list[StoredFile]:
        """把上传内容写入暂存目录，返回服务端落盘清单。"""
        staging = self.staging_dir(token)
        staging.mkdir(parents=True, exist_ok=True)
        stored: list[StoredFile] = []
        for original_name, data in files:
            digest = hashlib.sha256(data).hexdigest()
            is_index = _base_name(original_name).casefold() == INDEX_FILE_NAME
            if is_index:
                storage_name = INDEX_FILE_NAME
                path = self._child(staging, storage_name)
                relative = f"{STAGING_DIR_NAME}/{token}/{storage_name}"
            else:
                docs = staging / DOCS_DIR_NAME
                docs.mkdir(parents=True, exist_ok=True)
                storage_name = stored_name(digest, original_name)
                path = self._child(docs, storage_name)
                relative = f"{STAGING_DIR_NAME}/{token}/{DOCS_DIR_NAME}/{storage_name}"
            self._atomic_write(path, data)
            stored.append(
                StoredFile(
                    original_name=_base_name(original_name),
                    storage_name=storage_name,
                    relative_path=relative,
                    sha256=digest,
                    size=len(data),
                    is_index=is_index,
                )
            )
        return stored

    def write_manifest(self, token: str, payload: dict[str, Any]) -> Path:
        staging = self.staging_dir(token)
        path = self._child(staging, MANIFEST_FILE_NAME)
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        self._atomic_write(path, encoded.encode("utf-8"))
        return path

    def promote(self, token: str, kb_id: str) -> Path:
        """把暂存目录原子 rename 为 ``knowledge-bases/<kbId>``。"""
        source = self.staging_dir(token)
        target = self.target_dir(kb_id)
        if not source.is_dir():
            raise FileNotFoundError("staging directory missing")
        if target.exists():
            raise FileExistsError("knowledge base directory already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        return target

    def discard(self, token: str) -> None:
        shutil.rmtree(self.staging_dir(token), ignore_errors=True)

    def remove(self, kb_id: str) -> None:
        shutil.rmtree(self.target_dir(kb_id), ignore_errors=True)

    def move_to_trash(self, kb_id: str) -> Path | None:
        source = self.target_dir(kb_id)
        if not source.exists():
            return None
        self.trash_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        target = self.trash_root / f"{kb_id}-{stamp}"
        os.replace(source, target)
        return target

    # --- 孤儿扫描 -----------------------------------------------------------

    def scan_orphans(
        self, known_ids: Collection[str], *, max_age: timedelta
    ) -> int:
        """删除「有目录但 DB 无对应行」且 mtime 早于 ``max_age`` 的目录。"""
        if not self.root.exists():
            return 0
        removed = 0
        now = datetime.now(timezone.utc).timestamp()
        for entry in self.root.iterdir():
            if (
                entry.is_symlink()
                or not entry.is_dir()
                or not KB_ID_PATTERN.match(entry.name)
            ):
                continue
            if entry.name in known_ids:
                continue
            try:
                age = now - entry.stat().st_mtime
            except FileNotFoundError:
                continue
            if age <= max_age.total_seconds():
                continue
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1
        return removed

    # --- 内部 ---------------------------------------------------------------

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.part")
        try:
            with tmp.open("wb") as handle:
                for offset in range(0, len(data), WRITE_CHUNK_BYTES):
                    handle.write(data[offset : offset + WRITE_CHUNK_BYTES])
            os.replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise


def _base_name(original_name: str) -> str:
    return original_name.replace("\\", "/").rsplit("/", 1)[-1]


__all__ = [
    "DOCS_DIR_NAME",
    "INDEX_FILE_NAME",
    "KbStorage",
    "KnowledgePathError",
    "MANIFEST_FILE_NAME",
    "STAGING_DIR_NAME",
    "StoredFile",
    "slugify",
    "stored_name",
]
