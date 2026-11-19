"""跨 spec InjectionPreparer 契约。用例名带 TC 编号。

知识库导入/检索/失效判定/正文组装的实现与用例属 knowledge-base spec，本 spec 不重复。
"""

from __future__ import annotations

import inspect

from workbench.core.ports import (
    InjectionItem,
    InjectionPreparer,
    InjectionSnapshot,
    InvalidCodeRef,
    KnowledgeRef,
    PreparedInjection,
    get_injection_preparer,
    register_injection_preparer,
)


def test_tc068_preparer_contract() -> None:
    sig = inspect.signature(InjectionPreparer.prepare_for_call)
    assert list(sig.parameters) == [
        "self",
        "session_id",
        "project_id",
        "prompt",
        "knowledge_refs",
        "confirm_invalid_codes",
    ]
    for name in (
        "session_id",
        "project_id",
        "prompt",
        "knowledge_refs",
        "confirm_invalid_codes",
    ):
        assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY

    assert set(KnowledgeRef.__dataclass_fields__) == {"kb_id", "entry_codes"}
    assert set(InvalidCodeRef.__dataclass_fields__) == {"kb_id", "code"}
    assert set(PreparedInjection.__dataclass_fields__) == {"prepared", "snapshot"}
    assert set(InjectionSnapshot.__dataclass_fields__) == {
        "items",
        "prompt_chars",
        "injected_chars",
        "total_chars",
        "excluded_codes",
    }
    assert set(InjectionItem.__dataclass_fields__) == {
        "kb_id",
        "kb_name",
        "kb_version",
        "entry_codes",
        "injected_chars",
    }

    register_injection_preparer(None)
    assert get_injection_preparer() is None

    class Dummy:
        async def prepare_for_call(self, **kwargs):  # noqa: ANN003, ANN201
            raise NotImplementedError

    dummy = Dummy()
    register_injection_preparer(dummy)  # type: ignore[arg-type]
    try:
        assert get_injection_preparer() is dummy
    finally:
        register_injection_preparer(None)
        assert get_injection_preparer() is None
