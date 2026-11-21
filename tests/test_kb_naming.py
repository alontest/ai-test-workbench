"""知识库名称推导。用例名带 TC 编号。"""

from __future__ import annotations

from workbench.knowledge.naming import derive_name, name_key

SHA = "0123456789abcdef" + "0" * 48


def test_tc108_derives_name_in_fixed_order() -> None:
    assert derive_name("  表单名  ", {"name": "顶层"}, SHA) == "表单名"
    assert derive_name(None, {"name": "顶层"}, SHA) == "顶层"
    assert derive_name("", {"meta": {"name": "元名"}}, SHA) == "元名"
    assert (
        derive_name(
            None,
            {
                "meta": {
                    "source": {"files": [{"path": "exports/pay/index.json"}]}
                }
            },
            SHA,
        )
        == "pay"
    )
    assert (
        derive_name(
            None, {"meta": {"graph_fingerprint": "abcdef123456"}}, SHA
        )
        == "知识库 abcdef12"
    )
    assert derive_name(None, {}, SHA) == "知识库 01234567"

    # 显式名称为空白时继续回退。
    assert derive_name("   ", {"name": "顶层"}, SHA) == "顶层"

    assert name_key("  Payment PAY ") == "payment pay"
    assert len(derive_name("长" * 300, {}, SHA)) == 200
