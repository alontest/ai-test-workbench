"""知识库请求体模型。响应体由服务层直接组装为 camelCase JSON。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from workbench.services.knowledge.import_service import NAME_MAX_CHARS


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class KnowledgeImportForm(_CamelModel):
    """``POST /knowledge-bases`` 的 multipart 表单字段。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
    )

    project_id: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=NAME_MAX_CHARS)


class KnowledgeImportResponse(_CamelModel):
    kb: dict[str, Any]
    import_report: dict[str, Any]


class KnowledgeInjectionRef(_CamelModel):
    """预览请求里的扁平选中项：一条编号一个引用。"""

    kb_id: str = Field(min_length=1, max_length=32)
    code: str = Field(min_length=1, max_length=128)


class KnowledgePreviewRequest(_CamelModel):
    refs: list[KnowledgeInjectionRef]
    user_prompt: str = Field(min_length=1)


__all__ = [
    "KnowledgeImportForm",
    "KnowledgeImportResponse",
    "KnowledgeInjectionRef",
    "KnowledgePreviewRequest",
]
