"""QA 技能库与审批中心 API 测试（TC-303 ~ TC-308）。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from helpers import (
    build_client,
    make_app,
    seed_admin,
    seed_model,
    seed_project,
    seed_provider,
)
from workbench.db.models import AiCallRecord
from workbench.services.ai_gateway import AiGateway
from workbench.services.skills import BUILTIN_TEST_CASE_SKILL_SLUG

ADMIN = "test-admin-secret"
ORIGIN = {"origin": "http://testserver"}


class FakeSkillProposalAdapter:
    def __init__(self, revised_markdown: str) -> None:
        self.revised_markdown = revised_markdown
        self.calls: list[dict] = []

    async def complete(self, **kwargs) -> str:  # noqa: ANN003
        self.calls.append(kwargs)
        return self.revised_markdown

    async def test_connection(self, **kwargs):  # pragma: no cover
        raise NotImplementedError


async def _login(client) -> None:  # noqa: ANN001
    resp = await client.post(
        "/api/v1/auth/login",
        json={"password": ADMIN},
        headers=ORIGIN,
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_tc303_builtin_skill_seed_and_list_filtering(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)
    async with build_client(app) as client:
        await _login(client)

        first = await client.get("/api/v1/skills")
        assert first.status_code == 200
        items = first.json()["items"]
        assert len(items) == 1
        builtin = items[0]
        assert builtin["slug"] == BUILTIN_TEST_CASE_SKILL_SLUG
        assert builtin["scope"] == "global"
        assert builtin["projectId"] is None
        assert builtin["isBuiltin"] is True
        assert builtin["currentVersion"] == 1
        assert "阶段 1" in builtin["contentMd"]
        assert "阶段 2" in builtin["contentMd"]

        # 重复调用幂等，不产生重复内置种子
        second = await client.get("/api/v1/skills")
        assert second.status_code == 200
        assert len(second.json()["items"]) == 1

        detail = await client.get(f"/api/v1/skills/{builtin['skillId']}")
        assert detail.status_code == 200
        body = detail.json()
        assert len(body["versions"]) == 1
        assert body["versions"][0]["version"] == 1
        assert body["versions"][0]["sourceType"] == "builtin"


@pytest.mark.asyncio
async def test_tc304_create_and_update_skills_with_scope_uniqueness(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    p1 = await seed_project(database.sessionmaker, "订单中心")
    p2 = await seed_project(database.sessionmaker, "库存中心")
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)

        # 1. 创建全局技能
        g_resp = await client.post(
            "/api/v1/skills",
            headers=ORIGIN,
            json={
                "scope": "global",
                "slug": "payment-security-checklist",
                "name": "支付安全测试规范",
                "domain": "test-case",
                "description": "金额篡改、越权与重放攻击检查",
                "triggers": ["case-library"],
                "contentMd": "# 支付安全规范 v1\n- 校验签名与金额一致性",
            },
        )
        assert g_resp.status_code == 201
        g_skill = g_resp.json()
        assert g_skill["currentVersion"] == 1
        assert g_skill["versions"][0]["sourceType"] == "human"

        # 2. 同全局作用域重复 slug -> 409
        dup_global = await client.post(
            "/api/v1/skills",
            headers=ORIGIN,
            json={
                "scope": "global",
                "slug": "payment-security-checklist",
                "name": "重复全局技能",
                "domain": "test-case",
                "description": "重复",
                "contentMd": "# dup",
            },
        )
        assert dup_global.status_code == 409
        assert dup_global.json()["code"] == "skill_slug_duplicate"

        # 3. 项目 p1 下可使用同 slug 创建项目专属技能
        p1_resp = await client.post(
            "/api/v1/skills",
            headers=ORIGIN,
            json={
                "scope": "project",
                "projectId": p1,
                "slug": "payment-security-checklist",
                "name": "订单中心定制安全规范",
                "domain": "test-case",
                "description": "订单专属",
                "contentMd": "# 订单专属安全规范 v1",
            },
        )
        assert p1_resp.status_code == 201
        p1_skill = p1_resp.json()
        assert p1_skill["scope"] == "project"
        assert p1_skill["projectId"] == p1

        # 4. 按 projectId 查询：p1 能看到全局 + p1 专属；p2 只能看到全局
        list_p1 = await client.get(f"/api/v1/skills?projectId={p1}")
        assert list_p1.status_code == 200
        ids_p1 = {item["skillId"] for item in list_p1.json()["items"]}
        assert g_skill["skillId"] in ids_p1
        assert p1_skill["skillId"] in ids_p1

        list_p2 = await client.get(f"/api/v1/skills?projectId={p2}")
        assert list_p2.status_code == 200
        ids_p2 = {item["skillId"] for item in list_p2.json()["items"]}
        assert g_skill["skillId"] in ids_p2
        assert p1_skill["skillId"] not in ids_p2

        # 5. 人工编辑升级版本为 v2
        upd = await client.put(
            f"/api/v1/skills/{p1_skill['skillId']}",
            headers=ORIGIN,
            json={
                "name": "订单中心定制安全规范（修订）",
                "contentMd": "# 订单专属安全规范 v2\n- 增加优惠券并发扣减检查",
                "changeSummary": "补充优惠券并发条款",
            },
        )
        assert upd.status_code == 200
        updated = upd.json()
        assert updated["currentVersion"] == 2
        assert "优惠券并发扣减" in updated["contentMd"]
        assert [v["version"] for v in updated["versions"]] == [2, 1]
        assert updated["versions"][0]["changeSummary"] == "补充优惠券并发条款"


@pytest.mark.asyncio
async def test_tc305_rollback_skill_appends_new_version_without_erasing_history(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    app = make_app(settings, database)

    async with build_client(app) as client:
        await _login(client)

        created = (
            await client.post(
                "/api/v1/skills",
                headers=ORIGIN,
                json={
                    "scope": "global",
                    "slug": "order-state-machine-skill",
                    "name": "状态机测试技能",
                    "domain": "test-case",
                    "description": "状态跃迁覆盖",
                    "contentMd": "# 版本 1 正文",
                },
            )
        ).json()
        skill_id = created["skillId"]

        await client.put(
            f"/api/v1/skills/{skill_id}",
            headers=ORIGIN,
            json={"contentMd": "# 版本 2 正文", "changeSummary": "升级到 v2"},
        )
        await client.put(
            f"/api/v1/skills/{skill_id}",
            headers=ORIGIN,
            json={"contentMd": "# 版本 3 正文", "changeSummary": "升级到 v3"},
        )

        # 回滚到 v1 -> 生成 v4（sourceType='rollback'），保留 1/2/3 全部历史
        rb = await client.post(
            f"/api/v1/skills/{skill_id}/rollback",
            headers=ORIGIN,
            json={"targetVersion": 1},
        )
        assert rb.status_code == 200
        rolled = rb.json()
        assert rolled["currentVersion"] == 4
        assert rolled["contentMd"] == "# 版本 1 正文"
        assert [v["version"] for v in rolled["versions"]] == [4, 3, 2, 1]
        assert rolled["versions"][0]["sourceType"] == "rollback"

        # 回滚不存在的版本号 -> 404
        missing = await client.post(
            f"/api/v1/skills/{skill_id}/rollback",
            headers=ORIGIN,
            json={"targetVersion": 99},
        )
        assert missing.status_code == 404
        assert missing.json()["code"] == "skill_version_not_found"


@pytest.mark.asyncio
async def test_tc306_propose_skill_revision_via_ai_gateway_creates_pending_approval_without_mutating_skill(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "结算中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)

    revised_md = (
        "# 两阶段测试设计与用例生成规范（v0 底座）\n\n"
        "## 一、核心原则\n"
        "1. **先设计后铺开**：禁止越过检查点确认。\n"
        "2. **分布式锁与幂等专项**：所有涉及资金扣减的检查点必须包含幂等键重放与锁超时场景。\n"
    )
    adapter = FakeSkillProposalAdapter(f"```markdown\n{revised_md}\n```")
    gateway = AiGateway(adapter=adapter, retry_backoff=0)
    app = make_app(settings, database, ai_gateway=gateway)

    async with build_client(app) as client:
        await _login(client)

        skills_resp = await client.get("/api/v1/skills")
        builtin = skills_resp.json()["items"][0]
        skill_id = builtin["skillId"]
        original_md = builtin["contentMd"]

        prop_resp = await client.post(
            f"/api/v1/skills/{skill_id}/proposals",
            headers=ORIGIN,
            json={
                "projectId": project_id,
                "modelId": model_id,
                "instruction": "增加分布式锁超时与资金扣减幂等键重放的专项检查要求",
            },
        )
        assert prop_resp.status_code == 201
        approval = prop_resp.json()
        assert approval["status"] == "pending"
        assert approval["targetType"] == "qa_skill"
        assert approval["targetId"] == skill_id
        assert approval["baseVersion"] == 1
        assert approval["beforeContent"] == original_md
        assert "分布式锁与幂等专项" in approval["afterContent"]
        assert "--- a/two-stage-test-case-design.md (v1)" in approval["unifiedDiff"]
        assert "+++ b/two-stage-test-case-design.md (proposed)" in approval["unifiedDiff"]
        assert "+2. **分布式锁与幂等专项**" in approval["unifiedDiff"]
        assert approval["sessionId"] is not None
        assert approval["callId"] is not None

        # 验证真的走了唯一模型出口 AiGateway.complete 并落盘 AiCallRecord
        assert len(adapter.calls) == 1
        async with database.sessionmaker() as db:
            call_count = await db.scalar(
                select(func.count()).select_from(AiCallRecord)
            )
            assert call_count == 1

        # 关键红线：在人工批准前，原技能绝不能被静默修改！
        skill_after_propose = (
            await client.get(f"/api/v1/skills/{skill_id}")
        ).json()
        assert skill_after_propose["currentVersion"] == 1
        assert skill_after_propose["contentMd"] == original_md
        assert len(skill_after_propose["versions"]) == 1


@pytest.mark.asyncio
async def test_tc307_approve_proposal_updates_skill_and_records_agent_proposal_version(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "账务中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)

    revised_md = "# 两阶段测试设计规范（AI 修订 v2）\n\n- 新增对账差错与冲正幂等检查点要求"
    adapter = FakeSkillProposalAdapter(revised_md)
    gateway = AiGateway(adapter=adapter, retry_backoff=0)
    app = make_app(settings, database, ai_gateway=gateway)

    async with build_client(app) as client:
        await _login(client)
        builtin = (await client.get("/api/v1/skills")).json()["items"][0]
        skill_id = builtin["skillId"]

        proposal = (
            await client.post(
                f"/api/v1/skills/{skill_id}/proposals",
                headers=ORIGIN,
                json={
                    "projectId": project_id,
                    "modelId": model_id,
                    "instruction": "补充对账差错与冲正幂等检查点要求",
                },
            )
        ).json()
        approval_id = proposal["approvalId"]

        # 审批中心列表过滤 pending
        pending_list = await client.get(
            f"/api/v1/approvals?status=pending&projectId={project_id}"
        )
        assert pending_list.status_code == 200
        assert [item["approvalId"] for item in pending_list.json()["items"]] == [
            approval_id
        ]

        # 批准提案
        approved_resp = await client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=ORIGIN,
            json={"decisionNote": "QA 负责人审核通过，准予入库"},
        )
        assert approved_resp.status_code == 200
        approved = approved_resp.json()
        assert approved["status"] == "approved"
        assert approved["appliedVersion"] == 2
        assert approved["decisionNote"] == "QA 负责人审核通过，准予入库"
        assert approved["decidedAt"] is not None

        # 目标技能已升级为 v2，且版本历史记录 sourceType='agent_proposal' 与 approvalId
        skill_detail = (await client.get(f"/api/v1/skills/{skill_id}")).json()
        assert skill_detail["currentVersion"] == 2
        assert skill_detail["contentMd"] == revised_md
        assert [v["version"] for v in skill_detail["versions"]] == [2, 1]
        v2 = skill_detail["versions"][0]
        assert v2["sourceType"] == "agent_proposal"
        assert v2["approvalId"] == approval_id
        assert v2["sessionId"] == proposal["sessionId"]


@pytest.mark.asyncio
async def test_tc308_reject_proposal_preserves_skill_and_blocks_double_decision(
    settings, database
) -> None:
    await seed_admin(database.sessionmaker, ADMIN)
    project_id = await seed_project(database.sessionmaker, "营销中心")
    provider_id = await seed_provider(database.sessionmaker)
    model_id = await seed_model(database.sessionmaker, provider_id)

    adapter = FakeSkillProposalAdapter("# 被驳回的草稿内容")
    gateway = AiGateway(adapter=adapter, retry_backoff=0)
    app = make_app(settings, database, ai_gateway=gateway)

    async with build_client(app) as client:
        await _login(client)
        builtin = (await client.get("/api/v1/skills")).json()["items"][0]
        skill_id = builtin["skillId"]
        original_md = builtin["contentMd"]

        proposal = (
            await client.post(
                f"/api/v1/skills/{skill_id}/proposals",
                headers=ORIGIN,
                json={
                    "projectId": project_id,
                    "modelId": model_id,
                    "instruction": "删掉所有现有规则",
                },
            )
        ).json()
        approval_id = proposal["approvalId"]

        # 驳回提案
        rej_resp = await client.post(
            f"/api/v1/approvals/{approval_id}/reject",
            headers=ORIGIN,
            json={"decisionNote": "不能删减核心两阶段规范，予以驳回"},
        )
        assert rej_resp.status_code == 200
        rejected = rej_resp.json()
        assert rejected["status"] == "rejected"
        assert rejected["appliedVersion"] is None
        assert rejected["decisionNote"] == "不能删减核心两阶段规范，予以驳回"
        assert rejected["decidedAt"] is not None

        # 原技能保持 v1 毫发无损
        skill_detail = (await client.get(f"/api/v1/skills/{skill_id}")).json()
        assert skill_detail["currentVersion"] == 1
        assert skill_detail["contentMd"] == original_md
        assert len(skill_detail["versions"]) == 1

        # 重复批准或重复驳回已决审批单 -> 409 approval_already_decided
        again_approve = await client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            headers=ORIGIN,
        )
        assert again_approve.status_code == 409
        assert again_approve.json()["code"] == "approval_already_decided"

        again_reject = await client.post(
            f"/api/v1/approvals/{approval_id}/reject",
            headers=ORIGIN,
        )
        assert again_reject.status_code == 409
        assert again_reject.json()["code"] == "approval_already_decided"
