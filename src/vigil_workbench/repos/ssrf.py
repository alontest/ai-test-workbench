"""出站地址 SSRF 防护：仅公网 https origin、仅 443（ADR-213）。"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable, Sequence
from urllib.parse import urlsplit

from vigil_workbench.repos.errors import RepoValidationError

HostResolver = Callable[[str], Sequence[str]]

_IP_LITERAL = re.compile(r"[0-9.]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_ALLOWED_PORTS = (None, 443)
INVALID_API_BASE_URL_MESSAGE = "仅允许 https 公网 origin 且端口为 443。"


class _UnsafeOrigin(ValueError):
    pass


def _default_resolver(host: str) -> Sequence[str]:
    infos = socket.getaddrinfo(
        host, 443, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM
    )
    return [info[4][0] for info in infos]


def _is_public_address(text: str) -> bool:
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    mapped = getattr(address, "ipv4_mapped", None)
    if mapped is not None:
        address = mapped
    return address.is_global and not address.is_multicast


def _normalize_host(host: str) -> str:
    normalized = host.strip().lower().rstrip(".")
    if not normalized or "%" in normalized:
        # 空主机、IPv6 zone id（fe80::1%eth0）一律拒绝
        raise _UnsafeOrigin
    if _IP_LITERAL.fullmatch(normalized) and _parse_ip(normalized) is None:
        # 前导零等歧义写法可能被解析成另一地址
        raise _UnsafeOrigin
    return normalized


def _parse_ip(text: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(text)
    except ValueError:
        return None


def _resolve(resolver: HostResolver, host: str) -> list[str]:
    try:
        addresses = list(resolver(host))
    except (OSError, ValueError) as exc:
        raise _UnsafeOrigin from exc
    if not addresses:
        raise _UnsafeOrigin
    return addresses


def assert_public_https_origin(
    url: str, *, resolver: HostResolver | None = None
) -> str:
    """返回归一化 origin；任何非公网、非 https-443 的输入抛 ``invalid_api_base_url``。"""
    try:
        normalized = _normalize_origin(url, resolver or _default_resolver)
    except _UnsafeOrigin as exc:
        raise RepoValidationError(
            "invalid_api_base_url",
            INVALID_API_BASE_URL_MESSAGE,
            details=[{"field": "apiBaseUrl", "message": INVALID_API_BASE_URL_MESSAGE}],
        ) from exc
    return normalized


def _normalize_origin(url: str, resolver: HostResolver) -> str:
    if not isinstance(url, str):
        raise _UnsafeOrigin
    text = url
    if not text or _CONTROL.search(text) or any(ch.isspace() for ch in text):
        raise _UnsafeOrigin
    if "\\" in text:
        raise _UnsafeOrigin
    parts = urlsplit(text)
    if parts.scheme.lower() != "https":
        raise _UnsafeOrigin
    if parts.username is not None or parts.password is not None:
        raise _UnsafeOrigin
    if parts.query or parts.fragment:
        raise _UnsafeOrigin
    if parts.path not in ("", "/"):
        raise _UnsafeOrigin
    if parts.hostname is None:
        raise _UnsafeOrigin
    try:
        port = parts.port
    except ValueError as exc:
        raise _UnsafeOrigin from exc
    if port not in _ALLOWED_PORTS:
        raise _UnsafeOrigin
    host = _normalize_host(parts.hostname)
    for address in _resolve(resolver, host):
        if not _is_public_address(address):
            raise _UnsafeOrigin
    return f"https://[{host}]" if ":" in host else f"https://{host}"


__all__ = ["HostResolver", "assert_public_https_origin"]
