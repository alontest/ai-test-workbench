import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { EntrancePage } from "./EntrancePage";

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/entrances/:key" element={<EntrancePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const ITEMS = [
  {
    key: "log-triage",
    name: "排查日志",
    description: "从日志片段中归纳异常链路与排查线索。",
    domain: "diagnosis",
    status: "planned" as const,
  },
  {
    key: "bug-analysis",
    name: "分析 bug",
    description: "结合缺陷描述与项目上下文定位根因。",
    domain: "diagnosis",
    status: "live" as const,
  },
];

describe("TC-054 占位页说明所属域与状态", () => {
  test("TC-054 占位页含域名、状态、返回首页且无输入控件", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ITEMS }));
    renderAt("/entrances/log-triage");
    expect(await screen.findByRole("heading", { name: "排查日志" })).toBeInTheDocument();
    expect(screen.getByText(/diagnosis/)).toBeInTheDocument();
    expect(screen.getByText(/规划中|计划中/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /返回首页/ })).toHaveAttribute("href", "/");
    expect(screen.getByText(/不会创建会话/)).toBeInTheDocument();
    expect(screen.getByText(/不会调用模型/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /提交|发起调用|创建会话/ })).not.toBeInTheDocument();
  });
});

describe("TC-055 占位页无副作用", () => {
  test("TC-055 渲染占位页不发起写请求", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ITEMS }));
    renderAt("/entrances/log-triage");
    await screen.findByRole("heading", { name: "排查日志" });
    const methods = api.fetch.mock.calls.map((call) => {
      const input = call[0] as RequestInfo;
      const init = call[1] as RequestInit | undefined;
      if (init?.method) {
        return init.method.toUpperCase();
      }
      if (typeof input === "object" && input !== null && "method" in input) {
        return String((input as Request).method || "GET").toUpperCase();
      }
      return "GET";
    });
    expect(methods.every((method) => method === "GET")).toBe(true);
  });
});

describe("TC-056 入口状态由配置驱动", () => {
  test("TC-056 live 渲染挂载点而非占位文案", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ITEMS }));
    renderAt("/entrances/bug-analysis");
    expect(await screen.findByTestId("entrance-live")).toBeInTheDocument();
    expect(screen.queryByText(/不会创建会话/)).not.toBeInTheDocument();
  });

  test("TC-056 配置缺失显示错误态", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/entrances", () => jsonResponse({ items: ITEMS }));
    renderAt("/entrances/unknown");
    expect(await screen.findByText(/入口不存在|已被移除/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /返回首页/ })).toHaveAttribute("href", "/");
  });
});
