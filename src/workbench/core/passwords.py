"""管理员口令哈希：Argon2id 编码串整体存储。"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_HASHER = PasswordHasher()


def hash_password(password: str) -> str:
    return _HASHER.hash(password)


def verify_password(encoded: str, password: str) -> bool:
    if not encoded or not password:
        return False
    try:
        return _HASHER.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False
