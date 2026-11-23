"""假 InjectionPreparer：只锁定 core 契约，不实现知识库检索/组装。

知识库导入/检索/失效判定/正文组装属 knowledge-base spec，本 spec 不重复。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from vigil_workbench.core.ports import (
    InjectionItem,
    InjectionSnapshot,
    InvalidCodeRef,
    KnowledgeRef,
    PreparedInjection,
)
from vigil_workbench.services.errors import (
    KnowledgeInvalidEntriesError,
    KnowledgeInjectionEmptyError,
    PromptBudgetExceededError,
)

KB_ID = "3f2504e04f8911d39a0c0305e82c3301"


class ScriptedInjectionPreparer:
    def __init__(self) -> None:
        self.invalid_items: list[dict[str, object]] = []
        self.empty_after_confirm = False
        self.budget: dict[str, int] | None = None
        self.prepared = "知识块请分析"
        self.snapshot = InjectionSnapshot(
            items=(
                InjectionItem(
                    kb_id=KB_ID,
                    kb_name="支付中心知识库",
                    kb_version=2,
                    entry_codes=("ENT-012", "BR-003"),
                    injected_chars=3,
                ),
            ),
            prompt_chars=3,
            injected_chars=3,
            total_chars=6,
            excluded_codes=("ENT-009",),
        )
        self.calls: list[dict[str, Any]] = []

    async def prepare_for_call(
        self,
        *,
        session_id: int,
        project_id: int,
        prompt: str,
        knowledge_refs: Sequence[KnowledgeRef],
        confirm_invalid_codes: Sequence[InvalidCodeRef],
    ) -> PreparedInjection:
        self.calls.append(
            {
                "session_id": session_id,
                "project_id": project_id,
                "prompt": prompt,
                "knowledge_refs": list(knowledge_refs),
                "confirm_invalid_codes": list(confirm_invalid_codes),
            }
        )
        if self.budget is not None:
            raise PromptBudgetExceededError(**self.budget)
        if self.invalid_items:
            expected = {(item["kbId"], item["code"]) for item in self.invalid_items}
            confirmed = {(ref.kb_id, ref.code) for ref in confirm_invalid_codes}
            if confirmed != expected:
                raise KnowledgeInvalidEntriesError(self.invalid_items)
        if self.empty_after_confirm:
            raise KnowledgeInjectionEmptyError()
        return PreparedInjection(prepared=self.prepared, snapshot=self.snapshot)
