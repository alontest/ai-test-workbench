"""知识库域错误族。

只承载错误码、计数、编号与行号；**不携带正文、摘要或字段值**（ADR-114）。
继承 ``DomainError`` 以便 API 层沿用统一错误体映射。
"""

from __future__ import annotations

from collections.abc import Sequence

from workbench.services.errors import DomainError

INDEX_JSON_INVALID = "index_json_invalid"


class KbDomainError(DomainError):
    """知识库域错误基类。"""


class IndexJsonError(KbDomainError):
    """``index.json`` 整包不可导入；``reason`` 是固定枚举码。"""

    def __init__(
        self,
        reason: str,
        *,
        line: int | None = None,
        column: int | None = None,
        count: int | None = None,
        limit: int | None = None,
    ) -> None:
        detail: dict[str, object] = {"message": reason}
        if line is not None:
            detail["line"] = line
        if column is not None:
            detail["column"] = column
        if count is not None:
            detail["count"] = count
        if limit is not None:
            detail["limit"] = limit
        super().__init__(
            INDEX_JSON_INVALID,
            "index.json 不合法，无法导入。",
            status_code=400,
            details=[detail],
        )
        self.reason = reason
        self.line = line
        self.column = column
        self.count = count
        self.limit = limit


class KnowledgeInvalidEntriesError(KbDomainError):
    def __init__(self, invalid_items: Sequence[dict[str, object]]) -> None:
        super().__init__(
            "knowledge_invalid_entries",
            "部分知识库条目已失效，确认后才能继续。",
            status_code=409,
            details={"invalidItems": list(invalid_items)},
        )


class KnowledgeInjectionEmptyError(KbDomainError):
    def __init__(self) -> None:
        super().__init__(
            "knowledge_injection_empty",
            "确认后没有可注入的知识库条目。",
            status_code=409,
        )


class PromptBudgetExceededError(KbDomainError):
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


__all__ = [
    "INDEX_JSON_INVALID",
    "IndexJsonError",
    "KbDomainError",
    "KnowledgeInjectionEmptyError",
    "KnowledgeInvalidEntriesError",
    "PromptBudgetExceededError",
]
