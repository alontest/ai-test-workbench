"""仓库令牌加解密、掩码与脱敏。用例名带 TC 编号。"""

from __future__ import annotations

import uuid

import pytest

from workbench.core.crypto import CredentialUnavailable
from workbench.repos.crypto import decrypt_token, encrypt_token, mask_token
from workbench.repos.errors import RepoProviderError
from workbench.repos.redaction import redact_provider_exception, safe_log_fields
from workbench.repos.types import ProviderError

KEY = bytes(range(32, 64))
OTHER_KEY = bytes(range(32))


def test_tc201_token_encrypted_with_repo_key_and_returned_as_mask() -> None:
    token = "ghp_" + uuid.uuid4().hex
    ciphertext = encrypt_token(token, key=KEY)

    assert ciphertext.startswith("v1:")
    assert token not in ciphertext
    assert decrypt_token(ciphertext, key=KEY) == token
    assert mask_token(token) == "ghp_****" + token[-4:]

    assert mask_token("abc") == "****"
    assert mask_token("") == ""
    assert mask_token("abcdefghijkl") == "****ijkl"
    assert mask_token("sk-" + "x" * 20) == "sk-****" + "xxxx"


def test_tc204_update_token_rotates_ciphertext_and_mask() -> None:
    old_token = "ghp_aaaa1111"
    new_token = "glpat-abcde5040"

    old_ciphertext = encrypt_token(old_token, key=KEY)
    new_ciphertext = encrypt_token(new_token, key=KEY)

    assert old_ciphertext != new_ciphertext
    assert encrypt_token(old_token, key=KEY) != old_ciphertext
    assert decrypt_token(old_ciphertext, key=KEY) == old_token
    assert decrypt_token(new_ciphertext, key=KEY) == new_token
    assert mask_token(old_token) != mask_token(new_token)
    assert mask_token(new_token) == "glpat-****5040"


def test_tc246_token_never_in_errors_or_log_fields() -> None:
    token = "ghp_" + uuid.uuid4().hex
    ciphertext = encrypt_token(token, key=KEY)

    attempts = (
        {"key": OTHER_KEY},
        {"key": KEY, "revoked": True},
    )
    for kwargs in attempts:
        with pytest.raises(CredentialUnavailable) as err:
            decrypt_token(ciphertext, **kwargs)
        text = str(err.value)
        assert token not in text
        assert ciphertext not in text
        assert token[:12] not in text

    for empty in (None, ""):
        with pytest.raises(CredentialUnavailable) as err:
            decrypt_token(empty, key=KEY)
        assert token not in str(err.value)

    error = ProviderError(
        "auth", status_code=401, message=f"raw supplier text {token}"
    )
    mapped = RepoProviderError(error, provider="github", binding_id="b1")
    assert token not in str(mapped)
    assert token not in str(mapped.details)
    assert mapped.code == "provider_auth_failed"

    fields = safe_log_fields(
        {
            "bindingId": "b1",
            "provider": "github",
            "repoKey": "github:pay/checkout",
            "statusCode": 401,
            "category": "auth",
            "token": token,
            "ciphertext": ciphertext,
            "body": token,
        }
    )
    assert set(fields) == {
        "bindingId",
        "provider",
        "repoKey",
        "statusCode",
        "category",
    }
    assert token not in str(fields)

    redacted = redact_provider_exception(
        error, provider="github", binding_id="b1", repo_key="github:pay/checkout"
    )
    assert set(redacted) <= {
        "provider",
        "bindingId",
        "repoKey",
        "statusCode",
        "category",
    }
    assert token not in str(redacted)
