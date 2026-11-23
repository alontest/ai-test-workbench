"""服务层统一领域错误，由 API 层映射为错误体。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

Details = Sequence[Mapping[str, object]] | Mapping[str, object]


def coerce_details(
    details: Details | None,
) -> list[dict[str, object]] | dict[str, object]:
    if details is None:
        return []
    if isinstance(details, Mapping) and not isinstance(details, Sequence):
        return dict(details)
    return [dict(item) for item in details]


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: Details | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = coerce_details(details)
        self.headers = dict(headers or {})

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return f"DomainError(code={self.code!r})"


class KnowledgeInvalidEntriesError(DomainError):
    def __init__(self, invalid_items: Sequence[Mapping[str, object]]) -> None:
        super().__init__(
            "knowledge_invalid_entries",
            "知识库条目已失效，请确认后重试。",
            status_code=409,
            details={"invalidItems": list(invalid_items)},
        )


class KnowledgeInjectionEmptyError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "knowledge_injection_empty",
            "确认后没有可注入的知识库条目。",
            status_code=409,
        )


class PromptBudgetExceededError(DomainError):
    def __init__(
        self,
        *,
        prompt_chars: int,
        injected_chars: int,
        total_chars: int,
        limit: int,
    ) -> None:
        super().__init__(
            "prompt_budget_exceeded",
            "提示与注入合计超过字符上限。",
            status_code=400,
            details={
                "promptChars": prompt_chars,
                "injectedChars": injected_chars,
                "totalChars": total_chars,
                "limit": limit,
            },
        )
