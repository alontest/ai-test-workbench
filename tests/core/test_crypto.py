"""AES-256-GCM 与掩码。用例名带 TC 编号。"""

from __future__ import annotations

import base64

import pytest

from vigil_workbench.core.crypto import CredentialUnavailable, decrypt, encrypt, mask_secret

KEY = bytes(range(32))
OTHER_KEY = bytes(range(32, 64))


def test_tc017_crypto_roundtrip_and_tamper() -> None:
    token = encrypt("sk-abcdef1234", key=KEY)
    assert token.startswith("v1:")
    _, nonce_b64, cipher_b64 = token.split(":")
    assert len(base64.b64decode(nonce_b64)) == 12
    assert base64.b64decode(cipher_b64)
    assert decrypt(token, key=KEY) == "sk-abcdef1234"

    # 每次 nonce 随机
    assert encrypt("same", key=KEY) != encrypt("same", key=KEY)

    cipher_bytes = bytearray(base64.b64decode(cipher_b64))
    cipher_bytes[0] ^= 0x01
    tampered = f"v1:{nonce_b64}:{base64.b64encode(bytes(cipher_bytes)).decode()}"
    for bad in (
        tampered,
        "v2:" + token[3:],
        "v1:not-base64:also-bad",
        "v1:" + nonce_b64 + ":" + base64.b64encode(b"x").decode(),
    ):
        with pytest.raises(CredentialUnavailable) as err:
            decrypt(bad, key=KEY)
        assert token not in str(err.value)

    with pytest.raises(CredentialUnavailable):
        decrypt(token, key=OTHER_KEY)


def test_tc017_mask_secret_edges() -> None:
    secret = "sk-" + "e77adff78a"
    assert mask_secret(secret) == "sk-****" + secret[-4:]
    assert mask_secret("sk-1234") == "sk-****1234"
    assert mask_secret("") == ""
    assert mask_secret("abc") == "****"
    assert mask_secret("abcdef") == "****cdef"
