"""自动上下文推荐与 `test-case` 两阶段生成 / 用例库 / 导出接口。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from vigil_workbench.api.deps import require_same_origin
from vigil_workbench.services import context_recommender
from vigil_workbench.services import test_cases as test_cases_service

router = APIRouter(tags=["test-cases"], dependencies=[Depends(require_same_origin)])


def _gateway(request: Request):  # noqa: ANN202
    gateway = getattr(request.app.state, "ai_gateway", None)
    if gateway is None:
        from vigil_workbench.services.ai_gateway import AiGateway

        gateway = AiGateway()
        request.app.state.ai_gateway = gateway
    return gateway


class ContextRecommendationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    text: str
    limit: int = context_recommender.DEFAULT_LIMIT


class KbRefRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    kb_id: str = Field(alias="kbId")
    entry_codes: list[str] = Field(default_factory=list, alias="entryCodes")


class PlanCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    model_id: int = Field(alias="modelId")
    session_id: int | None = Field(default=None, alias="sessionId")
    skill_id: str | None = Field(default=None, alias="skillId")
    title: str
    requirement_text: str = Field(alias="requirementText")
    kb_refs: list[KbRefRequest] = Field(default_factory=list, alias="kbRefs")
    code_paths: list[str] = Field(default_factory=list, alias="codePaths")


class GenerateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    model_id: int | None = Field(default=None, alias="modelId")
    selected_checkpoint_ids: list[str] = Field(alias="selectedCheckpointIds")
    checkpoints_override: list[dict[str, Any]] | None = Field(
        default=None, alias="checkpointsOverride"
    )


class TestCaseUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    title: str | None = None
    module: str | None = None
    priority: str | None = None
    case_type: str | None = Field(default=None, alias="caseType")
    preconditions: list[str] | None = None
    steps: list[dict[str, Any]] | None = None
    expected_summary: str | None = Field(default=None, alias="expectedSummary")
    kb_links: list[dict[str, Any]] | None = Field(default=None, alias="kbLinks")
    code_paths: list[str] | None = Field(default=None, alias="codePaths")


@router.post("/projects/{project_id}/context-recommendations")
async def recommend_context(
    project_id: int, payload: ContextRecommendationRequest
) -> dict[str, object]:
    return await context_recommender.recommend(
        project_id, text=payload.text, limit=payload.limit
    )


@router.post("/projects/{project_id}/test-case-designs/plan", status_code=201)
async def create_plan(
    project_id: int, payload: PlanCreateRequest, request: Request
) -> dict[str, object]:
    return await test_cases_service.create_plan(
        project_id,
        model_id=payload.model_id,
        session_id=payload.session_id,
        skill_id=payload.skill_id,
        title=payload.title,
        requirement_text=payload.requirement_text,
        kb_refs=[
            {"kbId": ref.kb_id, "entryCodes": ref.entry_codes}
            for ref in payload.kb_refs
        ],
        code_paths=payload.code_paths,
        gateway=_gateway(request),
    )


@router.get("/test-case-designs/{plan_id}")
async def get_plan(plan_id: str) -> dict[str, object]:
    return await test_cases_service.get_plan(plan_id)


@router.get("/projects/{project_id}/test-case-designs")
async def list_plans(project_id: int) -> dict[str, object]:
    items = await test_cases_service.list_plans(project_id)
    return {"items": items}


@router.post("/test-case-designs/{plan_id}/generate")
async def generate_cases(
    plan_id: str, payload: GenerateRequest, request: Request
) -> dict[str, object]:
    return await test_cases_service.generate_cases(
        plan_id,
        selected_checkpoint_ids=payload.selected_checkpoint_ids,
        checkpoints_override=payload.checkpoints_override,
        model_id=payload.model_id,
        gateway=_gateway(request),
    )


@router.get("/projects/{project_id}/test-cases/export")
async def export_test_cases(
    project_id: int, format: str = Query(default="json")
) -> Response:
    result = await test_cases_service.export_test_cases(project_id, format=format)
    if result["format"] == "csv":
        return Response(
            content=result["content"], media_type="text/csv; charset=utf-8"
        )
    if result["format"] == "markdown":
        return Response(
            content=result["content"], media_type="text/markdown; charset=utf-8"
        )
    return JSONResponse({"items": result["items"]})


@router.get("/projects/{project_id}/test-cases")
async def list_test_cases(
    project_id: int,
    module: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    stale_only: bool = Query(default=False, alias="staleOnly"),
    q: str | None = Query(default=None),
) -> dict[str, object]:
    return await test_cases_service.list_test_cases(
        project_id,
        module=module,
        priority=priority,
        stale_only=stale_only,
        q=q,
    )


@router.get("/test-cases/{case_id}")
async def get_test_case(case_id: str) -> dict[str, object]:
    return await test_cases_service.get_test_case(case_id)


@router.patch("/test-cases/{case_id}")
async def update_test_case(
    case_id: str, payload: TestCaseUpdateRequest
) -> dict[str, object]:
    return await test_cases_service.update_test_case(
        case_id,
        title=payload.title,
        module=payload.module,
        priority=payload.priority,
        case_type=payload.case_type,
        preconditions=payload.preconditions,
        steps=payload.steps,
        expected_summary=payload.expected_summary,
        kb_links=payload.kb_links,
        code_paths=payload.code_paths,
    )


@router.delete("/test-cases/{case_id}", status_code=204)
async def delete_test_case(case_id: str) -> Response:
    await test_cases_service.delete_test_case(case_id)
    return Response(status_code=204)


@router.post("/test-cases/{case_id}/acknowledge-stale")
async def acknowledge_stale(case_id: str) -> dict[str, object]:
    return await test_cases_service.acknowledge_stale(case_id)
