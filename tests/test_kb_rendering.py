"""注入模板与字符预算。用例名带 TC 编号。"""

from __future__ import annotations

from datetime import datetime

from vigil_workbench.knowledge.rendering import render_injection
from vigil_workbench.knowledge.types import InjectionEntry

LIMIT = 200_000


def _entry(**overrides) -> InjectionEntry:
    values = {
        "kb_id": "kb-1",
        "kb_name": "支付域知识库",
        "kb_version": 2,
        "code": "ENT-1",
        "title": "订单",
        "body": "订单正文",
        "summary": "订单摘要",
        "generated_at": datetime(2026, 9, 28),
    }
    values.update(overrides)
    return InjectionEntry(**values)


def test_tc127_renders_injection_template_and_chars() -> None:
    entries = (
        _entry(),
        _entry(code="BR-2", title="退款规则", body="退款正文"),
    )
    result = render_injection(entries, "请分析", limit=LIMIT)

    expected_block = (
        "【知识库上下文】\n"
        "知识库：支付域知识库 v2（生成时间：2026-09-28T00:00:00）\n"
        "### ENT-1 订单\n"
        "订单正文\n"
        "### BR-2 退款规则\n"
        "退款正文\n"
        "\n"
    )
    assert result.injection_block == expected_block
    assert result.text == expected_block + "请分析"
    assert result.injected_chars == len(expected_block)
    assert result.prompt_chars == len("请分析")
    assert result.total_chars == len(result.text)
    assert result.over_limit is False
    assert [item.source for item in result.items] == ["body", "body"]


def test_tc128_uses_summary_and_marks_missing_body() -> None:
    entries = (
        _entry(body=None, summary="订单摘要"),
        _entry(code="ENT-2", body="   ", summary="空白正文摘要"),
        _entry(code="ENT-3", body=None, summary=""),
    )
    result = render_injection(entries, "提示", limit=LIMIT)

    assert "订单摘要（正文缺失）" in result.injection_block
    assert "空白正文摘要（正文缺失）" in result.injection_block
    assert [item.source for item in result.items] == ["summary", "summary", "summary"]
    assert all(item.content for item in result.items)
    assert result.items[2].content == "（正文缺失）"


def test_tc150_injection_block_carries_kb_name_and_generated_at() -> None:
    entries = (
        _entry(),
        _entry(
            kb_id="kb-2",
            kb_name="订单域知识库",
            kb_version=1,
            code="TERM-1",
            title="订单",
            generated_at=None,
        ),
    )
    result = render_injection(entries, "提示", limit=LIMIT)

    assert "知识库：支付域知识库 v2（生成时间：2026-09-28T00:00:00）" in result.injection_block
    assert "知识库：订单域知识库 v1（生成时间：未知）" in result.injection_block
