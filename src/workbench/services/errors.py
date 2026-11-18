"""服务层统一领域错误，由 API 层映射为错误体。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Sequence[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = list(details or ())

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"DomainError(code={self.code!r})"
