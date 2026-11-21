"""仓库绑定请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class RepoBindingCreate(_CamelModel):
    provider: str
    repo_identifier: str
    org_id: str | None = None
    api_base_url: str | None = None
    token: str


class RepoTokenUpdate(_CamelModel):
    token: str


class RepoConnectionTest(_CamelModel):
    provider: str
    repo_identifier: str
    org_id: str | None = None
    api_base_url: str | None = None
    token: str
