"""集中阈值常量：所有魔法数字的唯一来源。"""

from __future__ import annotations

from datetime import timedelta

PROMPT_MAX_CHARS = 200_000
MAX_ARTIFACT_BYTES = 10 * 1024 * 1024
MAX_FILES_PER_UPLOAD = 10
AI_ATTEMPT_TIMEOUT_SECONDS = 120
CONNECTION_TEST_TIMEOUT_SECONDS = 10
LOGIN_IDLE_TIMEOUT = timedelta(hours=8)
LOGIN_MAX_FAILURES = 5
LOGIN_FAILURE_WINDOW = timedelta(minutes=5)
LOGIN_LOCK_DURATION = timedelta(minutes=5)
PREVIEW_MAX_BYTES = 262_144
DUPLICATE_NAME_RETRY_LIMIT = 100
LOGIN_SESSION_RETENTION = timedelta(days=30)
LOGIN_ATTEMPT_RETENTION = timedelta(days=1)
ARTIFACT_ORPHAN_MAX_AGE = timedelta(hours=24)

ALLOWED_ARTIFACT_EXTENSIONS: tuple[str, ...] = (
    ".txt",
    ".md",
    ".markdown",
    ".log",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".sql",
)

MIME_TYPE_BY_EXTENSION: dict[str, str] = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".log": "text/plain",
    ".json": "application/json",
    ".yaml": "application/yaml",
    ".yml": "application/yaml",
    ".csv": "text/csv",
    ".sql": "application/sql",
}
