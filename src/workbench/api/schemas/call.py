"""调用请求体。"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KnowledgeRefBody(_CamelModel):
    kb_id: int
    entry_codes: list[str] = Field(default_factory=list)


class InvalidCodeBody(_CamelModel):
    kb_id: int
    code: str


class CallCompleteRequest(_CamelModel):
    prompt: str
    temperature: float | None = None
    max_tokens: int | None = None
    knowledge_refs: list[KnowledgeRefBody] | None = None
    confirm_invalid_codes: list[InvalidCodeBody] | None = None
