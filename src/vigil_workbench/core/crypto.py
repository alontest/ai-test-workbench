"""AES-256-GCM 加解密与密钥掩码。

密文格式：``v1:<nonce_b64>:<ciphertext_b64>``；nonce 每次随机 12 字节。
所有解密失败统一抛 :class:`CredentialUnavailable`，异常文本不含密文。
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VERSION = "v1"
_NONCE_BYTES = 12
_KEY_BYTES = 32
_MASK = "****"


class CredentialUnavailable(Exception):
    """凭据无法解密或格式非法。"""


def _default_key() -> bytes:
    from vigil_workbench.config import get_settings

    return get_settings().encryption_key_bytes


def _resolve_key(key: bytes | None) -> bytes:
    resolved = key if key is not None else _default_key()
    if len(resolved) != _KEY_BYTES:
        raise CredentialUnavailable("加密密钥不可用")
    return resolved


def encrypt(plaintext: str, *, key: bytes | None = None) -> str:
    nonce = os.urandom(_NONCE_BYTES)
    ciphertext = AESGCM(_resolve_key(key)).encrypt(nonce, plaintext.encode("utf-8"), None)
    return ":".join(
        (
            _VERSION,
            base64.b64encode(nonce).decode("ascii"),
            base64.b64encode(ciphertext).decode("ascii"),
        )
    )


def decrypt(token: str, *, key: bytes | None = None) -> str:
    try:
        version, nonce_b64, ciphertext_b64 = token.split(":")
        if version != _VERSION:
            raise CredentialUnavailable("凭据不可用")
        nonce = base64.b64decode(nonce_b64, validate=True)
        ciphertext = base64.b64decode(ciphertext_b64, validate=True)
        if len(nonce) != _NONCE_BYTES or not ciphertext:
            raise CredentialUnavailable("凭据不可用")
        plaintext = AESGCM(_resolve_key(key)).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except CredentialUnavailable:
        raise
    except (ValueError, InvalidTag, binascii.Error, UnicodeDecodeError) as exc:
        raise CredentialUnavailable("凭据不可用") from exc


def mask_secret(secret: str) -> str:
    if not secret:
        return ""
    if len(secret) <= 4:
        return _MASK
    prefix = ""
    dash = secret.find("-")
    if 0 < dash < len(secret) - 1 and dash <= 3:
        prefix = secret[: dash + 1]
    return f"{prefix}{_MASK}{secret[-4:]}"
