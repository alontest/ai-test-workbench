"""制品存储：目录隔离、原子移动、trash 与孤儿扫描。"""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote


class ArtifactNotFound(LookupError):
    """制品不存在或路径越界。"""


def _settings():
    from vigil_workbench.config import get_settings

    return get_settings()


def data_dir() -> Path:
    return _settings().data_path


def sessions_dir() -> Path:
    return data_dir() / "sessions"


def artifact_dir(session_id: int) -> Path:
    return sessions_dir() / str(session_id)


def tmp_dir() -> Path:
    return data_dir() / ".tmp"


def trash_dir() -> Path:
    return data_dir() / ".trash"


def ensure_session_dir(session_id: int) -> Path:
    directory = artifact_dir(session_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def safe_artifact_path(session_id: int, relative_path: str) -> Path:
    base = data_dir().resolve()
    decoded = unquote(relative_path)
    if "\x00" in decoded or "\\" in decoded or decoded.startswith("/"):
        raise ArtifactNotFound("artifact not found")
    parts = Path(decoded).parts
    if any(part in {"..", "."} for part in parts):
        raise ArtifactNotFound("artifact not found")
    if not parts or parts[0] != "sessions":
        raise ArtifactNotFound("artifact not found")

    candidate = (base / decoded).resolve()
    session_root = (base / "sessions" / str(session_id)).resolve()
    if not candidate.is_relative_to(session_root):
        raise ArtifactNotFound("artifact not found")
    if not candidate.exists():
        raise ArtifactNotFound("artifact not found")

    current = session_root
    for part in candidate.relative_to(session_root).parts:
        current = current / part
        if current.is_symlink():
            raise ArtifactNotFound("artifact not found")
    if session_root.is_symlink():
        raise ArtifactNotFound("artifact not found")
    return candidate


def move_to_trash(session_id: int) -> Path | None:
    source = artifact_dir(session_id)
    if not source.exists():
        return None
    trash = trash_dir()
    trash.mkdir(parents=True, exist_ok=True)
    target = trash / f"{session_id}-{uuid.uuid4().hex}"
    os.replace(source, target)
    return target


def _is_older_than(moment: float, max_age: timedelta) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    return now - moment > max_age.total_seconds()


def scan_orphans(max_age: timedelta) -> int:
    removed = 0
    tmp = tmp_dir()
    if tmp.exists():
        for entry in tmp.iterdir():
            try:
                if _is_older_than(entry.stat().st_mtime, max_age):
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
    trash = trash_dir()
    if trash.exists():
        for entry in trash.iterdir():
            try:
                if _is_older_than(entry.stat().st_mtime, max_age):
                    if entry.is_dir():
                        shutil.rmtree(entry)
                    else:
                        entry.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
    return removed
