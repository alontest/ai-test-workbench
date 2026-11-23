"""项目请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ProjectCreate(_CamelModel):
    name: str
    repo_url: str | None = None
    tech_stack: str | None = None
    requirement_source: str | None = None
    notes: str | None = None


class ProjectUpdate(_CamelModel):
    name: str | None = None
    repo_url: str | None = None
    tech_stack: str | None = None
    requirement_source: str | None = None
    notes: str | None = None
