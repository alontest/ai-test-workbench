"""会话与文本输入请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SessionCreate(_CamelModel):
    project_id: int
    entrance_key: str
    title: str
    model_id: int


class TextInputCreate(_CamelModel):
    title: str
    text: str
