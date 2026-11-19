import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { HomePage } from "./HomePage";

const ENTRANCES = [
  {
    key: "case-library",
    name: "用例库",
    description: "浏览与检索测试用例，并在库内发起用例生成。",
    domain: "test-case",
    status: "planned",
  },
  {
    key: "bug-analysis",
    name: "分析 bug",
    description: "结合缺陷描述与项目上下文定位根因。",
    domain: "diagnosis",
    status: "planned",
  },
  {
    key: "log-triage",
    name: "排查日志",
    description: "从日志片段中归纳异常链路与排查线索。",
    domain: "diagnosis",
    status: "planned",
  },
  {
    key: "sql-analysis",
    name: "分析 SQL",
    description: "分析 SQL 语义、执行风险与优化方向。",
    domain: "diagnosis",
    status: "planned",
  },
  {
    key: "regression-list",
    name: "生成回归清单",
    description: "根据变更范围整理回归检查项。",
    domain: "regression-list",
    status: "planned",
  },
  {
    key: "test-report",
    name: "生成测试报告",
    description: "汇总执行结果并生成结构化测试报告。",
    domain: "test-report",
    status: "planned",
  },
];

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TC-051 首页 6 入口卡片", () => {
  test("TC-051 渲染 6 张入口卡片含名称与用途", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ENTRANCES }));
    api.on("GET", "/api/v1/sessions", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    renderPage();
    for (const item of ENTRANCES) {
      const card = await screen.findByRole("link", { name: new RegExp(item.name) });
      expect(card).toHaveAttribute("href", `/entrances/${item.key}`);
      expect(card).toHaveTextContent(item.description);
      expect(card).toHaveTextContent(/规划中|计划中/);
    }
    expect(screen.getAllByRole("link", { name: /用例库|分析 bug|排查日志|分析 SQL|生成回归清单|生成测试报告/ })).toHaveLength(6);
    expect(screen.queryByText("生成测试用例")).not.toBeInTheDocument();
  });
});

describe("TC-031 最近会话空态", () => {
  test("TC-031 无会话时展示空态而不是错误", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ENTRANCES }));
    api.on("GET", "/api/v1/sessions", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    renderPage();
    expect(await screen.findByText(/还没有分析会话|还没有会话/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
