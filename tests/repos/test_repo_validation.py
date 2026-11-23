"""仓库标识、路径、ref、API 域名与 SSRF 校验。用例名带 TC 编号。"""

from __future__ import annotations

import pytest

from vigil_workbench.repos.errors import RepoValidationError
from vigil_workbench.repos.ssrf import assert_public_https_origin
from vigil_workbench.repos.validation import (
    GITHUB_API_BASE_URL,
    YUNXIAO_API_BASE_URL,
    normalize_repo_key,
    parse_repo_identifier,
    validate_api_base_url,
    validate_ref,
    validate_repo_path,
)

_PRIVATE_ADDRESSES = (
    "0.0.0.0",
    "10.1.2.3",
    "100.64.0.1",
    "127.0.0.1",
    "127.1.2.3",
    "169.254.169.254",
    "172.16.5.4",
    "172.31.255.255",
    "192.0.0.8",
    "192.0.2.10",
    "192.168.1.1",
    "198.18.0.1",
    "198.51.100.7",
    "203.0.113.9",
    "224.0.0.1",
    "240.0.0.1",
    "255.255.255.255",
)
_PRIVATE_V6_ADDRESSES = (
    "::",
    "::1",
    "::ffff:127.0.0.1",
    "fc00::1",
    "fd00::1",
    "fe80::1",
    "ff02::1",
    "2001:db8::1",
)
_PUBLIC_ADDRESSES = ("1.1.1.1", "8.8.8.8", "93.184.216.34")
_PUBLIC_V6_ADDRESSES = ("2606:4700:4700::1111",)


def _origin(host: str) -> str:
    return f"https://[{host}]" if ":" in host else f"https://{host}"


def _assert_code(exc_info: pytest.ExceptionInfo[RepoValidationError], code: str) -> None:
    assert exc_info.value.code == code
    assert exc_info.value.status_code == 400


def test_tc202_parse_repo_identifier_per_provider() -> None:
    github = parse_repo_identifier("github", "Pay/checkout")
    assert github.repo_id == "Pay/checkout"
    assert github.repo_name == "Pay/checkout"
    assert github.owner == "Pay"

    yunxiao_path = parse_repo_identifier("yunxiao", "group/sub/repo")
    assert yunxiao_path.repo_id == "group/sub/repo"
    assert yunxiao_path.owner is None

    yunxiao_numeric = parse_repo_identifier("yunxiao", "123456")
    assert yunxiao_numeric.repo_id == "123456"

    for value in ("", "   ", "owner", "a/b/c", "/repo", "owner/", "a/..", "a b/c"):
        with pytest.raises(RepoValidationError) as err:
            parse_repo_identifier("github", value)
        _assert_code(err, "invalid_repo_identifier")

    for value in ("a//b", "../x", "x/../y", "a b/c", "/a", "g/1/2/3/4/5/6/7/8/9/10"):
        with pytest.raises(RepoValidationError) as err:
            parse_repo_identifier("yunxiao", value)
        _assert_code(err, "invalid_repo_identifier")

    with pytest.raises(RepoValidationError) as err:
        parse_repo_identifier("gitlab", "owner/repo")
    _assert_code(err, "invalid_provider")

    assert normalize_repo_key("GitHub", "Pay/Checkout") == "github:pay/checkout"


def test_tc206_api_base_url_validation_and_provider_defaults() -> None:
    assert validate_api_base_url("github", None) == GITHUB_API_BASE_URL
    assert validate_api_base_url("github", "https://api.github.com/") == (
        GITHUB_API_BASE_URL
    )
    with pytest.raises(RepoValidationError) as err:
        validate_api_base_url("github", "https://github.com")
    _assert_code(err, "invalid_api_base_url")

    assert validate_api_base_url("yunxiao", None) == YUNXIAO_API_BASE_URL
    assert validate_api_base_url("yunxiao", "  ") == YUNXIAO_API_BASE_URL

    resolver = lambda _host: ["93.184.216.34"]  # noqa: E731
    assert validate_api_base_url(
        "yunxiao", "https://code.example.com", resolver=resolver
    ) == ("https://code.example.com")

    bad_urls = (
        "http://code.example.com",
        "https://code.example.com/api",
        "https://code.example.com?x=1",
        "https://code.example.com#frag",
        "https://code.example.com:8443",
        "https://user:not-a-real-secret@code.example.com",
    )
    for url in bad_urls:
        with pytest.raises(RepoValidationError) as err:
            validate_api_base_url("yunxiao", url, resolver=resolver)
        _assert_code(err, "invalid_api_base_url")

    with pytest.raises(RepoValidationError) as err:
        validate_api_base_url("yunxiao", "https://127.0.0.1")
    _assert_code(err, "invalid_api_base_url")

    with pytest.raises(RepoValidationError) as err:
        validate_api_base_url("gitlab", None)
    _assert_code(err, "invalid_provider")


def test_tc239_path_and_ref_rejected_before_request() -> None:
    invalid_paths = (
        "",
        "/etc/passwd",
        "\\windows\\system32",
        "../secret",
        "src/../../etc/passwd",
        "src/./main.py",
        "src//main.py",
        "src/\x00main.py",
        "src/\x01main.py",
        "src/" + "a" * 256,
        "a" * 1025,
    )
    for path in invalid_paths:
        with pytest.raises(RepoValidationError) as err:
            validate_repo_path(path)
        _assert_code(err, "invalid_path")

    assert validate_repo_path("src/main.py") == "src/main.py"
    assert validate_repo_path("a b/c.txt") == "a b/c.txt"

    invalid_refs = (
        "",
        "..",
        "a..b",
        "@{upstream}",
        "a b",
        "a~1",
        "a^",
        "a:b",
        "a?",
        "a*",
        "a[",
        "a\\b",
        "/main",
        "main/",
        "a//b",
        "a" * 256,
    )
    for ref in invalid_refs:
        with pytest.raises(RepoValidationError) as err:
            validate_ref(ref)
        _assert_code(err, "invalid_ref")

    assert validate_ref("main") == "main"
    assert validate_ref("feature/pay-callback_2.0") == "feature/pay-callback_2.0"


def test_tc252_ssrf_blocks_private_reserved_and_non_443() -> None:
    for address in _PRIVATE_ADDRESSES:
        with pytest.raises(RepoValidationError) as err:
            assert_public_https_origin(_origin(address))
        _assert_code(err, "invalid_api_base_url")

    for address in _PRIVATE_V6_ADDRESSES:
        with pytest.raises(RepoValidationError) as err:
            assert_public_https_origin(_origin(address))
        _assert_code(err, "invalid_api_base_url")

    for address in _PUBLIC_ADDRESSES:
        assert assert_public_https_origin(_origin(address)) == _origin(address)

    for address in _PUBLIC_V6_ADDRESSES:
        assert assert_public_https_origin(_origin(address)) == _origin(address)

    for url in (
        "http://8.8.8.8",
        "https://8.8.8.8:8443",
        "https://8.8.8.8/api",
        "https://8.8.8.8?x=1",
        "https://8.8.8.8#f",
        "https://user:not-a-real-secret@8.8.8.8",
        " https://8.8.8.8",
        "https://8.8.8.8\\@127.0.0.1",
        "https://010.0.0.1",
        "https://localhost",
    ):
        with pytest.raises(RepoValidationError) as err:
            assert_public_https_origin(url)
        _assert_code(err, "invalid_api_base_url")

    with pytest.raises(RepoValidationError):
        assert_public_https_origin(
            "https://code.example.com", resolver=lambda _host: ["10.0.0.5"]
        )
    with pytest.raises(RepoValidationError):
        assert_public_https_origin(
            "https://code.example.com",
            resolver=lambda _host: ["8.8.8.8", "127.0.0.1"],
        )
    with pytest.raises(RepoValidationError):
        assert_public_https_origin(
            "https://code.example.com", resolver=lambda _host: []
        )

    def _boom(_host: str) -> list[str]:
        raise OSError("dns down")

    with pytest.raises(RepoValidationError):
        assert_public_https_origin("https://code.example.com", resolver=_boom)

    assert (
        assert_public_https_origin(
            "https://code.example.com", resolver=lambda _host: ["93.184.216.34"]
        )
        == "https://code.example.com"
    )
