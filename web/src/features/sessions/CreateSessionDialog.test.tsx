import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { StatusPill } from "./StatusPill";
import { SessionsPage } from "./SessionsPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <SessionsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-026 创建会话缺前置禁用", () => {
  test("TC-026 缺项目时禁用提交并给出配置引导", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/sessions", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("GET", "/api/v1/models", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建会话/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: /创建/ })).toBeDisabled();
    expect(within(dialog).getByRole("link", { name: /项目/ })).toHaveAttribute(
      "href",
      "/projects",
    );
  });

  test("TC-026 有项目缺启用模型时禁用提交并引导配置模型", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/sessions", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({
        items: [
          {
            projectId: 1,
            name: "支付中心",
            repoUrl: null,
            techStack: null,
            requirementSource: null,
            notes: null,
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    api.on("GET", "/api/v1/models", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建会话/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("button", { name: /创建/ })).toBeDisabled();
    expect(within(dialog).getByRole("link", { name: /模型|提供商/ })).toHaveAttribute(
      "href",
      "/providers",
    );
  });
});

describe("TC-027 筛选空态", () => {
  test("TC-027 无筛选时空态与筛选后空态文案不同", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({
        items: [
          {
            projectId: 1,
            name: "支付中心",
            repoUrl: null,
            techStack: null,
            requirementSource: null,
            notes: null,
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    api.on("GET", "/api/v1/models", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("GET", /\/api\/v1\/sessions/, (_request, url) => {
      const status = url.searchParams.get("status");
      if (status === "failed") {
        return jsonResponse({ items: [], nextCursor: null });
      }
      return jsonResponse({
        items: [
          {
            sessionId: 42,
            project: { projectId: 1, name: "支付中心" },
            entranceKey: "bug-analysis",
            title: "订单超时排查",
            status: "in_progress",
            model: {
              modelId: 3,
              modelName: "gpt-4.1",
              displayName: "GPT-4.1",
              providerId: 1,
              providerName: "OpenAI",
            },
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
            closedAt: null,
          },
        ],
        nextCursor: null,
      });
    });
    const { user } = renderPage();
    expect(await screen.findByText("订单超时排查")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText(/状态/), "failed");
    expect(await screen.findByText(/没有符合筛选条件/)).toBeInTheDocument();
    expect(screen.queryByText(/还没有会话|暂无会话/)).not.toBeInTheDocument();
  });
});

describe("TC-029 状态徽标带文字", () => {
  test("TC-029 进行中/已完成/失败均有文字而非仅颜色", () => {
    const { rerender } = render(<StatusPill status="in_progress" />);
    expect(screen.getByText("进行中")).toBeInTheDocument();
    rerender(<StatusPill status="completed" />);
    expect(screen.getByText("已完成")).toBeInTheDocument();
    rerender(<StatusPill status="failed" />);
    expect(screen.getByText("失败")).toBeInTheDocument();
  });
});
