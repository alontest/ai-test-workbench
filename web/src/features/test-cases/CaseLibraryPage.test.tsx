import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { renderWithApp } from "../../test/render";
import { CaseLibraryPage } from "./CaseLibraryPage";

const FRESH_CASE = {
  caseId: "c1",
  caseCode: "TC-ORD-001",
  module: "订单中心/超时关单",
  title: "订单超时后自动关闭",
  priority: "P0",
  caseType: "functional",
  preconditions: ["订单已创建"],
  steps: [{ stepNo: 1, action: "等待超时", expected: "订单关闭" }],
  expectedSummary: "订单状态变为 closed",
  kbLinks: [
    {
      kbId: "kb1",
      kbNameKey: "order-domain",
      code: "BR-001",
      codeKey: "br-001",
      title: "订单超时关闭规则",
    },
  ],
  codePaths: ["src/order/close.py"],
  staleStatus: "fresh",
  staleReasons: [],
  staleDetails: [],
};

const STALE_CASE = {
  ...FRESH_CASE,
  caseId: "c2",
  caseCode: "TC-ORD-002",
  title: "退款补偿保持幂等",
  priority: "P1",
  caseType: "concurrency",
  staleStatus: "stale",
  staleReasons: ["entry_modified"],
  staleDetails: [
    {
      code: "BR-001",
      kbNameKey: "order-domain",
      reason: "entry_modified",
      message: "知识条目 BR-001 的内容已更新。",
    },
  ],
};

const SUMMARY = {
  totalCount: 2,
  staleCount: 1,
  freshCount: 1,
  byPriority: { P0: 1, P1: 1, P2: 0, P3: 0 },
  moduleTree: [
    {
      name: "订单中心",
      count: 2,
      children: [{ name: "超时关单", count: 2, children: [] }],
    },
  ],
};

const RECOMMENDATION = {
  recommendedKbEntries: [
    {
      kbId: "kb1",
      kbName: "订单域知识库",
      code: "BR-001",
      title: "订单超时关闭规则",
      matchSource: "direct",
      viaCode: null,
    },
    {
      kbId: "kb1",
      kbName: "订单域知识库",
      code: "BR-002",
      title: "退款补偿说明",
      matchSource: "neighbor_1hop",
      viaCode: "BR-001",
    },
  ],
  recommendedCodePaths: [
    {
      path: "src/order/close.py",
      source: "kb_code_path",
      linkedKbCodes: ["BR-001"],
      bindingId: null,
    },
    {
      path: "src/order/refund.py",
      source: "recent_repo_read",
      linkedKbCodes: [],
      bindingId: "b1",
    },
    {
      path: "src/order/timeout.job",
      source: "input_path_mention",
      linkedKbCodes: [],
      bindingId: null,
    },
  ],
};

const PLAN = {
  planId: "p1",
  checkpoints: [
    {
      checkpointId: "CP-01",
      module: "订单中心/超时关单",
      scenario: "订单超时后自动关闭",
      category: "functional",
      priority: "P0",
      rationale: "引用 BR-001",
      kbCodes: ["BR-001"],
      codePaths: ["src/order/close.py"],
    },
    {
      checkpointId: "CP-02",
      module: "订单中心/超时关单",
      scenario: "退款补偿幂等",
      category: "concurrency",
      priority: "P2",
      rationale: "引用 BR-002",
      kbCodes: ["BR-002"],
      codePaths: [],
    },
  ],
};

function mockPickers(api: ReturnType<typeof installFetchMock>) {
  api.on("GET", "/api/v1/projects", () =>
    jsonResponse({
      items: [{ projectId: 1, name: "支付中心" }],
      nextCursor: null,
    }),
  );
  api.on("GET", "/api/v1/skills", () =>
    jsonResponse({
      items: [
        {
          skillId: "s1",
          name: "两阶段测试设计与用例生成规范",
          domain: "test-case",
        },
      ],
      nextCursor: null,
    }),
  );
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

async function openGenerator(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    await screen.findByRole("button", { name: /\+ 两阶段生成用例/ }),
  );
}

async function fillGenerator(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText("测试主题"), "订单超时关闭");
  await user.type(
    screen.getByLabelText("需求正文"),
    "BR-001 规定订单超时后关闭，代码在 src/order/close.py。",
  );
  await waitFor(() =>
    expect(screen.getByLabelText("提供商")).toHaveTextContent("OpenAI"),
  );
  await user.selectOptions(screen.getByLabelText("提供商"), "1");
  await waitFor(() =>
    expect(screen.getByLabelText("模型")).toHaveTextContent("GPT-4.1"),
  );
  await user.selectOptions(screen.getByLabelText("模型"), "7");
}

describe("TC-319 用例库两阶段生成", () => {
  test("TC-319 上下文推荐 → 检查点矩阵勾选 → 结构化用例入库", async () => {
    const api = installFetchMock();
    mockPickers(api);
    let generated = false;
    api.on("GET", "/api/v1/projects/1/test-cases", () =>
      jsonResponse(
        generated
          ? { items: [FRESH_CASE], summary: SUMMARY }
          : {
              items: [],
              summary: {
                totalCount: 0,
                staleCount: 0,
                freshCount: 0,
                byPriority: {},
                moduleTree: [],
              },
            },
      ),
    );
    let recommended = false;
    api.on(
      "POST",
      "/api/v1/projects/1/context-recommendations",
      () => {
        recommended = true;
        return jsonResponse(RECOMMENDATION);
      },
    );
    api.on("POST", "/api/v1/projects/1/test-case-designs/plan", () =>
      jsonResponse(PLAN, 201),
    );
    let generateBody: { selectedCheckpointIds?: string[] } = {};
    api.on("POST", "/api/v1/test-case-designs/p1/generate", async (request) => {
      generateBody = (await request.json()) as typeof generateBody;
      generated = true;
      return jsonResponse({ generatedCount: 1, items: [FRESH_CASE] });
    });

    const user = userEvent.setup();
    renderWithApp(<CaseLibraryPage />);

    await openGenerator(user);
    await fillGenerator(user);
    await user.click(screen.getByRole("button", { name: "智能推荐上下文" }));

    expect(await screen.findByText("direct 直命中")).toBeInTheDocument();
    expect(screen.getByText("neighbor_1hop 一跳邻居")).toBeInTheDocument();
    expect(screen.getByText("kb_code_path")).toBeInTheDocument();
    expect(screen.getByText("recent_repo_read")).toBeInTheDocument();
    expect(screen.getByText("input_path_mention")).toBeInTheDocument();
    expect(recommended).toBe(true);

    await user.click(screen.getByRole("button", { name: "生成检查点矩阵" }));
    expect(await screen.findByText("CP-01")).toBeInTheDocument();

    await user.click(
      screen.getByRole("checkbox", { name: /CP-02/ }),
    );
    await user.click(
      screen.getByRole("button", { name: "按勾选检查点生成用例" }),
    );

    await waitFor(() =>
      expect(generateBody.selectedCheckpointIds).toEqual(["CP-01"]),
    );
    expect(
      await screen.findByText(/已生成 1 条结构化用例/),
    ).toBeInTheDocument();
    const table = await screen.findByTestId("view-table");
    expect(within(table).getByText("TC-ORD-001")).toBeInTheDocument();
  });
});

describe("TC-320 用例库双视图、Stale 复核与导出", () => {
  test("TC-320 表格与层级树切换，确认复核恢复 fresh，多格式导出", async () => {
    const api = installFetchMock();
    mockPickers(api);
    let acknowledged = false;
    api.on("GET", "/api/v1/projects/1/test-cases", () =>
      jsonResponse({
        items: acknowledged ? [FRESH_CASE] : [FRESH_CASE, STALE_CASE],
        summary: acknowledged
          ? { ...SUMMARY, staleCount: 0, freshCount: 1, totalCount: 1 }
          : SUMMARY,
      }),
    );
    let acknowledgeCalled = false;
    api.on("POST", "/api/v1/test-cases/c2/acknowledge-stale", () => {
      acknowledgeCalled = true;
      acknowledged = true;
      return jsonResponse({ ...STALE_CASE, staleStatus: "fresh", staleReasons: [] });
    });
    api.on("GET", "/api/v1/projects/1/test-cases/export", () =>
      new Response("caseCode,title\nTC-ORD-001,订单超时后自动关闭\n", {
        status: 200,
        headers: { "Content-Type": "text/csv; charset=utf-8" },
      }),
    );

    const user = userEvent.setup();
    renderWithApp(<CaseLibraryPage />);

    const table = await screen.findByTestId("view-table");
    expect(within(table).getByText("TC-ORD-001")).toBeInTheDocument();
    expect(within(table).getAllByText("BR-001").length).toBeGreaterThan(0);
    expect(
      within(table).getAllByText("src/order/close.py").length,
    ).toBeGreaterThan(0);
    expect(within(table).getByText("知识条目 BR-001 的内容已更新。")).toBeInTheDocument();
    expect(await screen.findByTestId("stale-count")).toHaveTextContent("1");

    await user.click(screen.getByRole("button", { name: "确认复核" }));
    await waitFor(() => expect(acknowledgeCalled).toBe(true));
    await waitFor(() =>
      expect(
        screen.queryByText("知识条目 BR-001 的内容已更新。"),
      ).not.toBeInTheDocument(),
    );
    expect(await screen.findByTestId("stale-count")).toHaveTextContent("0");

    await user.click(screen.getByRole("button", { name: "层级树视图" }));
    const tree = await screen.findByTestId("view-tree");
    expect(within(tree).getByText("订单中心")).toBeInTheDocument();
    expect(within(tree).getByText("超时关单")).toBeInTheDocument();
    expect(within(tree).getByText("functional")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /导出 CSV/ }));
    expect(await screen.findByTestId("export-result")).toHaveTextContent(
      "TC-ORD-001",
    );

    await user.click(screen.getByRole("button", { name: /导出 JSON/ }));
    await waitFor(() =>
      expect(screen.getByTestId("export-result")).toHaveTextContent(
        "caseCode,title",
      ),
    );
  });
});
