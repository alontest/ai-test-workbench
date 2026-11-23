"""QA 技能库接口（/api/v1/skills）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from workbench.api.deps import require_same_origin
from workbench.services import skills as skills_service

router = APIRouter(
    prefix="/skills", tags=["skills"], dependencies=[Depends(require_same_origin)]
)


def _gateway(request: Request):  # noqa: ANN202
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is None:
        from workbench.services.ai_gateway import AiGateway

        gateway = AiGateway()
        request.app.state.ai_gateway = gateway
    return gateway


class SkillCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    scope: str = "global"
    project_id: int | None = Field(default=None, alias="projectId")
    slug: str
    name: str
    domain: str = "test-case"
    description: str
    triggers: list[str] = Field(default_factory=list)
    content_md: str = Field(alias="contentMd")
    change_summary: str = Field(
        default="人工创建初始版本", alias="changeSummary"
    )


class SkillUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    name: str | None = None
    description: str | None = None
    domain: str | None = None
    triggers: list[str] | None = None
    content_md: str = Field(alias="contentMd")
    change_summary: str = Field(
        default="人工修订技能正文", alias="changeSummary"
    )


class SkillProposalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    project_id: int | None = Field(default=None, alias="projectId")
    model_id: int | None = Field(default=None, alias="modelId")
    session_id: int | None = Field(default=None, alias="sessionId")
    instruction: str


class SkillRollbackRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    target_version: int = Field(alias="targetVersion")
    change_summary: str | None = Field(default=None, alias="changeSummary")


@router.get("")
async def list_skills(
    project_id: int | None = Query(default=None, alias="projectId"),
    domain: str | None = Query(default=None),
) -> dict[str, object]:
    items = await skills_service.list_skills(
        project_id=project_id,
        domain=domain,
    )
    return {"items": items}


@router.get("/{skill_id}")
async def get_skill(skill_id: str) -> dict[str, object]:
    return await skills_service.get_skill(skill_id)


@router.post("", status_code=201)
async def create_skill(payload: SkillCreateRequest) -> dict[str, object]:
    return await skills_service.create_skill(
        scope=payload.scope,
        project_id=payload.project_id,
        slug=payload.slug,
        name=payload.name,
        domain=payload.domain,
        description=payload.description,
        triggers=payload.triggers,
        content_md=payload.content_md,
        change_summary=payload.change_summary,
    )


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str, payload: SkillUpdateRequest
) -> dict[str, object]:
    return await skills_service.update_skill(
        skill_id,
        name=payload.name,
        description=payload.description,
        domain=payload.domain,
        triggers=payload.triggers,
        content_md=payload.content_md,
        change_summary=payload.change_summary,
    )


@router.post("/{skill_id}/proposals", status_code=201)
async def propose_skill_revision(
    skill_id: str, payload: SkillProposalRequest, request: Request
) -> dict[str, object]:
    return await skills_service.propose_skill_revision(
        skill_id,
        project_id=payload.project_id,
        model_id=payload.model_id,
        session_id=payload.session_id,
        instruction=payload.instruction,
        gateway=_gateway(request),
    )


@router.post("/{skill_id}/rollback")
async def rollback_skill(
    skill_id: str, payload: SkillRollbackRequest
) -> dict[str, object]:
    return await skills_service.rollback_skill(
        skill_id,
        target_version=payload.target_version,
        change_summary=payload.change_summary,
    )
