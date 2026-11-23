"""不透明分页游标：签名、跨查询复用与篡改。用例名带 TC 编号。"""

from __future__ import annotations

import pytest

from vigil_workbench.repos.cursor import (
    decode_page_cursor,
    derive_cursor_key,
    encode_page_cursor,
    fingerprint_query,
)
from vigil_workbench.repos.errors import RepoValidationError

KEY = derive_cursor_key(bytes(range(32, 64)))
CONTEXT = {
    "binding_id": "6f1c9a0e5b7d4c2a8e3f1b0d9c7a6e54",
    "provider": "github",
    "repo_key": "github:pay/checkout",
    "ref": "main",
    "path": "src",
    "query_fingerprint": fingerprint_query("checkout"),
}


def _encode(page: int, **overrides: object) -> str:
    context = {**CONTEXT, **overrides}
    return encode_page_cursor(key=KEY, page=page, **context)


def test_tc232_cursor_roundtrip_and_query_fingerprint() -> None:
    cursor = _encode(2)
    assert "." in cursor
    assert decode_page_cursor(cursor, key=KEY, **CONTEXT) == 2
    assert fingerprint_query("checkout") == fingerprint_query(" checkout ")
    assert fingerprint_query("checkout") != fingerprint_query("checkou")
    assert fingerprint_query(None) == fingerprint_query("")


def test_tc232_cursor_tamper_and_cross_query_rejected() -> None:
    cursor = _encode(3)
    body, signature = cursor.split(".")

    tampered = f"{body[:-1]}{'A' if body[-1] != 'A' else 'B'}.{signature}"
    bad_inputs = (
        tampered,
        f"{body}.{signature[:-1]}",
        cursor.replace(".", ""),
        "not-a-cursor",
    )
    for bad in bad_inputs:
        with pytest.raises(RepoValidationError) as err:
            decode_page_cursor(bad, key=KEY, **CONTEXT)
        assert err.value.code == "invalid_cursor"
        assert bad not in str(err.value)
        assert bad not in str(err.value.details)

    cross_queries = (
        {"binding_id": "0" * 32},
        {"repo_key": "github:other/repo"},
        {"ref": "develop"},
        {"path": "docs"},
        {"query_fingerprint": fingerprint_query("other")},
        {"provider": "yunxiao"},
    )
    for override in cross_queries:
        with pytest.raises(RepoValidationError) as err:
            decode_page_cursor(cursor, key=KEY, **{**CONTEXT, **override})
        assert err.value.code == "invalid_cursor"

    with pytest.raises(RepoValidationError):
        decode_page_cursor(cursor, key=derive_cursor_key(b"other-key"), **CONTEXT)
