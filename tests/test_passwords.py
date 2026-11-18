"""管理员口令哈希。用例名带 TC 编号。"""

from __future__ import annotations

from workbench.core.passwords import hash_password, verify_password


def test_tc002_password_verify_contract() -> None:
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert encoded.startswith("$argon2")
    assert verify_password(encoded, "correct horse battery staple") is True
    assert verify_password(encoded, "wrong") is False
    assert verify_password("not-an-argon2-encoded-string", "anything") is False
    assert verify_password("", "anything") is False
