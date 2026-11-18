"""提供商请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProviderCreate(_CamelModel):
    name: str
    protocol: str
    base_url: str
    api_key: str


class ProviderUpdate(_CamelModel):
    name: str | None = None
    protocol: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    enabled: bool | None = None


class ConnectionTestRequest(_CamelModel):
    protocol: str | None = None
    base_url: str | None = None
    api_key: str | None = None
