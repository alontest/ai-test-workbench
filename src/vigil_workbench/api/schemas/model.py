"""模型请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ModelCreate(_CamelModel):
    model_name: str
    display_name: str
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    enabled: bool | None = None


class ModelUpdate(_CamelModel):
    display_name: str | None = None
    default_temperature: float | None = None
    default_max_tokens: int | None = None
    enabled: bool | None = None
