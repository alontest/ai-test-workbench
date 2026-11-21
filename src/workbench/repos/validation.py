"""仓库标识、路径、ref、检索词与 API 域名的入口校验（ADR-213）。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from workbench.repos.errors import RepoValidationError
from workbench.repos.ssrf import HostResolver, assert_public_https_origin

GITHUB_API_BASE_URL = "https://api.github.com"
YUNXIAO_API_BASE_URL = "https://openapi-rdc.aliyuncs.com"
VALID_PROVIDERS = ("yunxiao", "github")

MAX_PATH_LENGTH = 1024
MAX_PATH_SEGMENT_LENGTH = 255
MAX_REF_LENGTH = 255
MAX_SEARCH_LENGTH = 100
MAX_REPO_NAME_LENGTH = 255
MAX_REPO_ID_LENGTH = 191

_GITHUB_SEGMENT = re.compile(r"[A-Za-z0-9._-]+")
_GITHUB_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+")
_YUNXIAO_REPO_ID = re.compile(r"[0-9]{1,64}")
_REF = re.compile(r"[A-Za-z0-9._/-]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_YUNXIAO_MAX_GROUP_DEPTH = 10


@dataclass(frozen=True)
class RepoIdentifier:
    repo_id: str
    repo_name: str
    owner: str | None = None


def _invalid(code: str, message: str, field: str) -> RepoValidationError:
    return RepoValidationError(
        code, message, details=[{"field": field, "message": message}]
    )


def validate_provider(provider: str) -> str:
    if provider not in VALID_PROVIDERS:
        raise _invalid(
            "invalid_provider", "provider 只能是 yunxiao 或 github。", "provider"
        )
    return provider


def _valid_segments(segments: list[str]) -> bool:
    return all(
        segment and segment not in (".", "..") and not _CONTROL.search(segment)
        and not any(ch.isspace() for ch in segment)
        for segment in segments
    )


def parse_repo_identifier(provider: str, value: str) -> RepoIdentifier:
    validate_provider(provider)
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        raise _invalid(
            "invalid_repo_identifier", "仓库标识不能为空。", "repoIdentifier"
        )

    if provider == "github":
        if not _GITHUB_IDENTIFIER.fullmatch(text):
            raise _invalid(
                "invalid_repo_identifier",
                "GitHub 仓库标识必须是 owner/repo。",
                "repoIdentifier",
            )
        owner, repo = text.split("/", 1)
        if (
            not _GITHUB_SEGMENT.fullmatch(owner)
            or not _GITHUB_SEGMENT.fullmatch(repo)
            or owner in (".", "..")
            or repo in (".", "..")
        ):
            raise _invalid(
                "invalid_repo_identifier",
                "GitHub 仓库标识必须是 owner/repo。",
                "repoIdentifier",
            )
        identifier = RepoIdentifier(repo_id=text, repo_name=text, owner=owner)
    else:
        if _YUNXIAO_REPO_ID.fullmatch(text):
            identifier = RepoIdentifier(repo_id=text, repo_name=text)
        else:
            segments = text.split("/")
            if (
                len(segments) > _YUNXIAO_MAX_GROUP_DEPTH
                or not _valid_segments(segments)
            ):
                raise _invalid(
                    "invalid_repo_identifier",
                    "云效仓库标识必须是 group/repo 全路径或数字仓库 ID。",
                    "repoIdentifier",
                )
            identifier = RepoIdentifier(repo_id=text, repo_name=text)

    if len(identifier.repo_name) > MAX_REPO_NAME_LENGTH:
        raise _invalid(
            "invalid_repo_identifier", "仓库标识过长。", "repoIdentifier"
        )
    if len(identifier.repo_id) > MAX_REPO_ID_LENGTH:
        raise _invalid(
            "invalid_repo_identifier", "仓库 ID 过长。", "repoIdentifier"
        )
    return identifier


def normalize_repo_key(provider: str, repo_name: str) -> str:
    key = f"{provider}:{repo_name}".casefold()
    if len(key) > MAX_REPO_NAME_LENGTH:
        raise _invalid("invalid_repo_identifier", "仓库标识过长。", "repoIdentifier")
    return key


def validate_repo_path(path: str) -> str:
    if not isinstance(path, str) or not path:
        raise _invalid("invalid_path", "文件路径不能为空。", "path")
    if len(path) > MAX_PATH_LENGTH:
        raise _invalid("invalid_path", "文件路径过长。", "path")
    if _CONTROL.search(path):
        raise _invalid("invalid_path", "文件路径含控制字符。", "path")
    if path.startswith(("/", "\\")) or "\\" in path:
        raise _invalid("invalid_path", "文件路径必须是相对路径。", "path")
    for segment in path.split("/"):
        if segment in ("", ".", ".."):
            raise _invalid("invalid_path", "文件路径不能包含空段或 .. 段。", "path")
        if len(segment) > MAX_PATH_SEGMENT_LENGTH:
            raise _invalid("invalid_path", "文件路径段过长。", "path")
    return path


def validate_ref(ref: str) -> str:
    if not isinstance(ref, str) or not ref:
        raise _invalid("invalid_ref", "ref 不能为空。", "ref")
    if len(ref) > MAX_REF_LENGTH:
        raise _invalid("invalid_ref", "ref 过长。", "ref")
    if not _REF.fullmatch(ref):
        raise _invalid("invalid_ref", "ref 含非法字符。", "ref")
    if ".." in ref or "@{" in ref:
        raise _invalid("invalid_ref", "ref 不能包含 .. 或 @{。", "ref")
    if ref.startswith("/") or ref.endswith("/") or "//" in ref:
        raise _invalid("invalid_ref", "ref 不能以 / 开头或结尾，也不能含空段。", "ref")
    return ref


def validate_search(value: str | None, *, max_chars: int = MAX_SEARCH_LENGTH) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _invalid("validation_error", "search 必须是字符串。", "search")
    text = value.strip()
    if not text:
        return None
    if len(text) > max_chars:
        raise _invalid(
            "validation_error", f"search 不能超过 {max_chars} 个字符。", "search"
        )
    return text


def validate_api_base_url(
    provider: str,
    api_base_url: str | None,
    *,
    resolver: HostResolver | None = None,
) -> str:
    """返回归一化 origin；GitHub 只接受固定域名，云效默认官方中心站。"""
    validate_provider(provider)
    candidate = api_base_url.strip() if isinstance(api_base_url, str) else ""
    if provider == "github":
        if not candidate:
            return GITHUB_API_BASE_URL
        if candidate.rstrip("/") != GITHUB_API_BASE_URL:
            raise _invalid(
                "invalid_api_base_url",
                "GitHub 只允许 https://api.github.com。",
                "apiBaseUrl",
            )
        return GITHUB_API_BASE_URL
    if not candidate:
        return YUNXIAO_API_BASE_URL
    return assert_public_https_origin(candidate, resolver=resolver)


__all__ = [
    "GITHUB_API_BASE_URL",
    "MAX_PATH_LENGTH",
    "MAX_REF_LENGTH",
    "MAX_SEARCH_LENGTH",
    "RepoIdentifier",
    "VALID_PROVIDERS",
    "YUNXIAO_API_BASE_URL",
    "normalize_repo_key",
    "parse_repo_identifier",
    "validate_api_base_url",
    "validate_provider",
    "validate_ref",
    "validate_repo_path",
    "validate_search",
]
