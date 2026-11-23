import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { renderWithApp } from "../../test/render";
import { ApprovalsPage } from "./ApprovalsPage";
import { SkillsPage } from "./SkillsPage";

const PROJECT = { projectId: 1, name: "支付中心" };

const SKILL = {
  skillId: "s1",
  scope: "global",
  projectId: null,
  slug: "two-stage-test-case-design",
  name: "两阶段测试设计与用例生成规范",
  domain: "test-case",
  description: "先检查点矩阵，再生成用例。",
  contentMd: "# 旧正文",
  currentVersion: 2,
  isBuiltin: true,
  createdAt: "2026-11-21T00:00:00Z",
  updatedAt: "2026-11-21T00:00:00Z",
};

const VERSIONS = [
  {
    versionId: "v2",
    version: 2,
    changeSummary: "人工修订技能正文",
    sourceType: "human",
    createdAt: "2026-11-21T02:00:00Z",
  },
  {
    versionId: "v1",
    version: 1,
    changeSummary: "系统内置初始版本",
    sourceType: "builtin",
    createdAt: "2026-11-21T01:00:00Z",
  },
];

const DETAIL = { ...SKILL, versions: VERSIONS };

const APPROVAL = {
  approvalId: "a1",
  projectId: 1,
  sessionId: 42,
  callId: 9,
  targetType: "qa_skill",
  targetId: "s1",
  targetTitle: "两阶段测试设计与用例生成规范",
  actionType: "update_skill",
  baseVersion: 2,
  beforeContent: "# 旧正文",
  afterContent: "# 新正文\n- 新增约束",
  unifiedDiff:
    "--- a/two-stage.md (v2)\n+++ b/two-stage.md (proposed)\n@@ -1 +1,2 @@\n-# 旧正文\n+# 新正文\n+- 新增约束",
  rationale: "补充并发与幂等检查点",
  status: "pending",
  decisionNote: null,
  appliedVersion: null,
  createdAt: "2026-11-21T03:00:00Z",
  decidedAt: null,
};

function mockSkillBase(api: ReturnType<typeof installFetchMock>) {
  api.on("GET", "/api/v1/projects", () =>
    jsonResponse({ items: [PROJECT], nextCursor: null }),
  );
  api.on("GET", "/api/v1/skills", () =>
    jsonResponse({ items: [SKILL], nextCursor: null }),
  );
  api.on("GET", "/api/v1/skills/s1", () => jsonResponse(DETAIL));
  api.on("GET", "/api/v1/providers", () =>
    jsonResponse({
      items: [{ providerId: 1, name: "OpenAI" }],
      nextCursor: null,
    }),
  );
  api.on("GET", "/api/v1/providers/1/models", () =>
    jsonResponse({
      items: [{ modelId: 7, modelName: "gpt-4.1", displayName: "GPT-4.1" }],
      nextCursor: null,
    }),
  );
}

describe("TC-318 QA 技能库", () => {
  test("TC-318 列表展示作用域与版本，支持保存正文与回滚", async () => {
    const api = installFetchMock();
    mockSkillBase(api);
    let saved: { contentMd?: string } = {};
    api.on("PUT", "/api/v1/skills/s1", async (request) => {
      saved = (await request.json()) as { contentMd?: string };
      return jsonResponse({
        ...DETAIL,
        contentMd: saved.contentMd,
        currentVersion: 3,
        versions: [
          {
            versionId: "v3",
            version: 3,
            changeSummary: "人工修订技能正文",
            sourceType: "human",
            createdAt: "2026-11-21T04:00:00Z",
          },
          ...VERSIONS,
        ],
      });
    });
    let rolledBack: { targetVersion?: number } = {};
    api.on("POST", "/api/v1/skills/s1/rollback", async (request) => {
      rolledBack = (await request.json()) as { targetVersion?: number };
      return jsonResponse({ ...DETAIL, currentVersion: 4 });
    });

    const user = userEvent.setup();
    renderWithApp(<SkillsPage />);

    expect(
      await screen.findByRole("heading", { level: 1, name: "QA 技能库" }),
    ).toBeInTheDocument();
    const listItem = await screen.findByRole("button", {
      name: /两阶段测试设计与用例生成规范/,
    });
    expect(listItem).toHaveTextContent("two-stage-test-case-design");
    expect(listItem).toHaveTextContent("global");
    expect(listItem).toHaveTextContent("v2");

    const editor = await screen.findByLabelText("技能正文");
    expect(editor).toHaveValue("# 旧正文");
    await user.clear(editor);
    await user.type(editor, "# 新正文");
    await user.click(screen.getByRole("button", { name: "保存正文" }));
    await waitFor(() => expect(saved.contentMd).toBe("# 新正文"));

    const rollbackButtons = screen.getAllByRole("button", {
      name: "回滚到此版本",
    });
    await user.click(rollbackButtons[rollbackButtons.length - 1]);
    await waitFor(() => expect(rolledBack.targetVersion).toBe(1));
  });

  test("TC-318 AI 修订生成 Unified Diff 提案并跳转审批中心", async () => {
    const api = installFetchMock();
    mockSkillBase(api);
    let proposed: { projectId?: number; modelId?: number; instruction?: string } = {};
    api.on("POST", "/api/v1/skills/s1/proposals", async (request) => {
      proposed = (await request.json()) as typeof proposed;
      return jsonResponse(APPROVAL, 201);
    });

    const user = userEvent.setup();
    renderWithApp(<SkillsPage />);

    await screen.findByLabelText("技能正文");
    await waitFor(() =>
      expect(screen.getByLabelText("提供商")).toHaveTextContent("OpenAI"),
    );
    await user.selectOptions(screen.getByLabelText("提供商"), "1");
    await waitFor(() =>
      expect(screen.getByLabelText("模型")).toHaveTextContent("GPT-4.1"),
    );
    await user.selectOptions(screen.getByLabelText("模型"), "7");
    await user.type(screen.getByLabelText("修订指令"), "补充并发与幂等检查点");
    await user.click(screen.getByRole("button", { name: "生成 Diff 提案" }));

    await waitFor(() => expect(proposed.modelId).toBe(7));
    expect(proposed.projectId).toBe(1);
    expect(proposed.instruction).toBe("补充并发与幂等检查点");
    const diff = await screen.findByTestId("proposal-diff");
    expect(diff).toHaveTextContent("+# 新正文");
    expect(
      screen.getByRole("link", { name: "前往审批中心" }),
    ).toHaveAttribute("href", "/extensions/approvals");
  });
});

describe("TC-318 审批中心", () => {
  test("TC-318 展示 Unified Diff 与理由，批准落盘", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/approvals", () =>
      jsonResponse({ items: [APPROVAL] }),
    );
    let approved = false;
    api.on("POST", "/api/v1/approvals/a1/approve", () => {
      approved = true;
      return jsonResponse({ ...APPROVAL, status: "approved", appliedVersion: 3 });
    });

    const user = userEvent.setup();
    renderWithApp(<ApprovalsPage />);

    expect(await screen.findByText("补充并发与幂等检查点")).toBeInTheDocument();
    expect(screen.getByLabelText("Unified Diff")).toHaveTextContent("+# 新正文");
    expect(screen.getByText(/会话 42/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "批准并落盘" }));
    await waitFor(() => expect(approved).toBe(true));
    expect(
      await screen.findByText(/已批准并落盘，技能当前版本 v3/),
    ).toBeInTheDocument();
  });

  test("TC-318 驳回携带审批备注且保留技能", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/approvals", () =>
      jsonResponse({ items: [APPROVAL] }),
    );
    let rejectedBody: { decisionNote?: string | null } = {};
    api.on("POST", "/api/v1/approvals/a1/reject", async (request) => {
      rejectedBody = (await request.json()) as typeof rejectedBody;
      return jsonResponse({ ...APPROVAL, status: "rejected" });
    });

    const user = userEvent.setup();
    renderWithApp(<ApprovalsPage />);

    await screen.findByText("补充并发与幂等检查点");
    await user.type(screen.getByLabelText("审批备注"), "暂不落盘");
    await user.click(screen.getByRole("button", { name: "驳回" }));

    await waitFor(() => expect(rejectedBody.decisionNote).toBe("暂不落盘"));
    expect(
      await screen.findByText("已驳回，技能正文保持不变。"),
    ).toBeInTheDocument();
  });
});
