"""仓库令牌加解密与掩码（ADR-204）。

算法与密文格式复用 ``workbench.core.crypto``，但密钥必须由调用方显式传入
``AW_REPO_TOKEN_KEY`` 的字节，禁止回落到模型密钥。
"""

from __future__ import annotations

from workbench.core.crypto import CredentialUnavailable
from workbench.core.crypto import decrypt as _core_decrypt
from workbench.core.crypto import encrypt as _core_encrypt

KEY_BYTES = 32
MASK = "****"
MIN_MASK_LENGTH = 12
PREFIX_SEARCH_LENGTH = 10
_UNAVAILABLE_MESSAGE = "仓库令牌不可用"


def _ensure_key(key: bytes) -> bytes:
    if len(key) != KEY_BYTES:
        raise CredentialUnavailable(_UNAVAILABLE_MESSAGE)
    return key


def encrypt_token(plaintext: str, *, key: bytes) -> str:
    return _core_encrypt(plaintext, key=_ensure_key(key))


def decrypt_token(
    ciphertext: str | None, *, key: bytes, revoked: bool = False
) -> str:
    """解绑或密文缺失一律拒绝；失败文案不含密文。"""
    if revoked or not ciphertext:
        raise CredentialUnavailable(_UNAVAILABLE_MESSAGE)
    _ensure_key(key)
    try:
        return _core_decrypt(ciphertext, key=key)
    except CredentialUnavailable as exc:
        raise CredentialUnavailable(_UNAVAILABLE_MESSAGE) from exc


def mask_token(token: str) -> str:
    """``<prefix>****<last4>``；短令牌整体掩码，空令牌保持空串。"""
    if not token:
        return ""
    if len(token) < MIN_MASK_LENGTH:
        return MASK
    prefix_end = 0
    for index, char in enumerate(token[:PREFIX_SEARCH_LENGTH]):
        if index > 0 and char in ("_", "-"):
            prefix_end = index + 1
            break
    return f"{token[:prefix_end]}{MASK}{token[-4:]}"


__all__ = [
    "KEY_BYTES",
    "MASK",
    "decrypt_token",
    "encrypt_token",
    "mask_token",
]
