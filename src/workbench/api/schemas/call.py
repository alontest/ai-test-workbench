"""调用请求体。"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

_KB_ID_MAX_LENGTH = 32


def _check_kb_id(value: str) -> str:
    if not value.strip():
        raise ValueError("知识库标识不能为空。")
    if len(value) > _KB_ID_MAX_LENGTH:
        raise ValueError(f"知识库标识长度不能超过 {_KB_ID_MAX_LENGTH}。")
    return value


_KbId = Annotated[str, AfterValidator(_check_kb_id)]


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KnowledgeRefBody(_CamelModel):
    kb_id: _KbId
    entry_codes: list[str] = Field(default_factory=list)


class InvalidCodeBody(_CamelModel):
    kb_id: _KbId
    code: str


class CallCompleteRequest(_CamelModel):
    prompt: str = Field(min_length=1)
    temperature: float | None = None
    max_tokens: int | None = None
    knowledge_refs: list[KnowledgeRefBody] | None = None
    confirm_invalid_codes: list[InvalidCodeBody] | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("提示不能为空白。")
        return value
