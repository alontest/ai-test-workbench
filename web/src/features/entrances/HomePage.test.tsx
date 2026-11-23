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
    description: "基于知识库规则与代码路径两阶段设计用例，支持溯源锚点、失效标红与多格式导出。",
    domain: "test-case",
    status: "live",
  },
  {
    key: "regression-list",
    name: "生成回归清单",
    description: "基于 Git 变更路径、本体一跳邻居与诊断结论三路召回，输出风险分级与漏测盲区。",
    domain: "regression-list",
    status: "planned",
  },
  {
    key: "test-report",
    name: "生成测试报告",
    description: "聚合用例执行率、回归覆盖度与诊断风险结论，产出带完整追溯编号的质量报告。",
    domain: "test-report",
    status: "planned",
  },
  {
    key: "bug-analysis",
    name: "分析 Bug",
    description: "联动报错信息、仓库源码与业务规则，按「假设 → 证据 → 结论」定位缺陷根因。",
    domain: "diagnosis",
    status: "planned",
  },
  {
    key: "log-triage",
    name: "排查日志",
    description: "从日志堆栈提取异常信号，自动关联对应版本源码与知识库条目收敛排查结论。",
    domain: "diagnosis",
    status: "planned",
  },
  {
    key: "sql-analysis",
    name: "分析 SQL",
    description: "结合 SQL、EXPLAIN 执行计划与知识库表结构（ENT-），诊断索引失效与锁竞争风险。",
    domain: "diagnosis",
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
      if (item.status === "live") {
        expect(card).toHaveTextContent("已上线");
      } else {
        expect(card).toHaveTextContent(/规划中|计划中/);
      }
    }
    expect(screen.getAllByRole("link", { name: /用例库|生成回归清单|生成测试报告|分析 Bug|排查日志|分析 SQL/ })).toHaveLength(6);
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
