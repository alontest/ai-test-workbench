"""供应商适配器注册表；服务层只通过 ``build_provider`` 取得实例。"""

from __future__ import annotations

import httpx

from vigil_workbench.repos.constants import REPO_HTTP_TIMEOUT_SECONDS
from vigil_workbench.repos.providers.base import BaseProvider
from vigil_workbench.repos.providers.github import GitHubProvider
from vigil_workbench.repos.providers.yunxiao import YunxiaoProvider
from vigil_workbench.repos.types import RepositoryRef

PROVIDER_CLASSES: dict[str, type[BaseProvider]] = {
    "github": GitHubProvider,
    "yunxiao": YunxiaoProvider,
}


def build_provider(
    ref: RepositoryRef,
    token: str,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = REPO_HTTP_TIMEOUT_SECONDS,
) -> BaseProvider:
    provider_class = PROVIDER_CLASSES.get(ref.provider)
    if provider_class is None:
        raise ValueError(f"未知供应商：{ref.provider}")
    return provider_class(ref, token, transport=transport, timeout=timeout)


__all__ = ["PROVIDER_CLASSES", "build_provider"]
