import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock } from "../test/fetch";
import { AppShell } from "./AppShell";

function LoginProbe() {
  const location = useLocation();
  return (
    <div>
      登录页
      <span data-testid="login-search">{location.search}</span>
    </div>
  );
}

function renderShell(route: string) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/login" element={<LoginProbe />} />
          <Route element={<AppShell />}>
            <Route path="*" element={<div>页面内容</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function breadcrumb(): HTMLElement {
  return screen.getByRole("navigation", { name: "面包屑" });
}

describe("AppShell 顶栏面包屑", () => {
  test.each([
    ["/", ["工作台", "首页"]],
    ["/sessions", ["工作台", "分析会话"]],
    ["/sessions/42", ["工作台", "分析会话", "会话详情"]],
    ["/providers", ["治理与系统", "AI 提供商"]],
    ["/providers/p1/models", ["治理与系统", "AI 提供商", "模型绑定"]],
    ["/calls", ["治理与系统", "调用记录"]],
    ["/projects/1/repos/9", ["上下文与资产", "项目上下文", "代码仓库"]],
    ["/repos", ["上下文与资产", "代码仓库"]],
    ["/knowledge-bases/kb1/entries/BL-001", ["上下文与资产", "知识库", "条目详情"]],
    ["/entrances/log-triage", ["测试与诊断", "排查日志"]],
    ["/entrances/bug-analysis", ["测试与诊断", "分析 Bug"]],
    ["/extensions/skills", ["上下文与资产", "QA 技能库"]],
    ["/extensions/mcp", ["上下文与资产", "MCP 工具源"]],
    ["/extensions/approvals", ["治理与系统", "审批中心"]],
    ["/extensions/history", ["治理与系统", "变更审计"]],
  ])("%s 显示对应层级且末项为当前位置", (route, crumbs) => {
    renderShell(route);
    const nav = breadcrumb();
    for (const crumb of crumbs) {
      expect(within(nav).getByText(crumb)).toBeInTheDocument();
    }
    expect(within(nav).getByText(crumbs[crumbs.length - 1])).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  test("顶栏不重复渲染页面标题 h1", () => {
    renderShell("/providers/p1/models");
    const topbar = screen.getByRole("banner");
    expect(within(topbar).queryByRole("heading")).not.toBeInTheDocument();
  });
});

describe("AppShell 侧栏分组与激活态", () => {
  test("按 4 大业务分组渲染导航且顺序对齐", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "主导航" });
    const headings = within(nav)
      .getAllByRole("heading", { level: 2 })
      .map((el) => el.textContent);
    expect(headings).toEqual([
      "工作台",
      "测试与诊断",
      "上下文与资产",
      "治理与系统",
    ]);
    expect(
      within(nav).getByRole("link", { name: "代码仓库" }),
    ).toHaveAttribute("href", "/repos");
  });

  test("当前路由对应的导航项标记 aria-current", () => {
    renderShell("/providers/p1/models");
    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(
      within(nav).getByRole("link", { name: "AI 提供商与模型" }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      within(nav).getByRole("link", { name: "项目上下文" }),
    ).not.toHaveAttribute("aria-current");
  });

  test("首页只在根路由激活", () => {
    renderShell("/");
    const nav = screen.getByRole("navigation", { name: "主导航" });
    expect(within(nav).getByRole("link", { name: "首页" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      within(nav).getByRole("link", { name: "分析会话" }),
    ).not.toHaveAttribute("aria-current");
  });
});

describe("AppShell 退出", () => {
  test("点击退出调用登出接口并跳转登录页", async () => {
    const api = installFetchMock();
    api.on(
      "POST",
      "/api/v1/auth/logout",
      () => new Response(null, { status: 204 }),
    );
    const user = userEvent.setup();
    renderShell("/providers");

    await user.click(screen.getByRole("button", { name: "退出" }));

    await waitFor(() => {
      expect(screen.getByText("登录页")).toBeInTheDocument();
    });
    expect(screen.getByTestId("login-search")).toHaveTextContent(
      "reason=logged-out",
    );
    expect(api.fetch).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
