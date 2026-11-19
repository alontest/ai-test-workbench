import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { CallsPage } from "./CallsPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <CallsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

const failedCall = {
  callId: 17,
  sessionId: 42,
  project: { projectId: 1, name: "支付中心" },
  model: { modelId: 3, displayName: "GPT-4.1", providerName: "OpenAI" },
  status: "failed",
  promptPreview: "请分析以下日志…",
  promptCharCount: 12,
  knowledgeInjection: null,
  latencyMs: 120000,
  retryCount: 1,
  errorCode: "timeout",
  errorMessage: "upstream request timed out",
  createdAt: "2026-11-18T02:30:00Z",
  finishedAt: "2026-11-18T02:32:00Z",
};

const successCall = {
  ...failedCall,
  callId: 18,
  status: "success",
  retryCount: 0,
  errorCode: null,
  errorMessage: null,
  latencyMs: 800,
};

function mockCommon(api: ReturnType<typeof installFetchMock>) {
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
  api.on("GET", "/api/v1/sessions", () =>
    jsonResponse({
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
    }),
  );
}

describe("TC-046 调用记录筛选与展开", () => {
  test("TC-046 列表按接口顺序展示并可展开失败行", async () => {
    const api = installFetchMock();
    mockCommon(api);
    api.on("GET", "/api/v1/calls", () =>
      jsonResponse({ items: [successCall, failedCall], nextCursor: null }),
    );
    api.on("GET", /\/api\/v1\/calls\/\d+$/, (_request, url) => {
      const id = Number(url.pathname.split("/").pop());
      if (id === 17) {
        return jsonResponse({ ...failedCall, resultText: null });
      }
      return jsonResponse({ ...successCall, resultText: "完整成功结果" });
    });
    const { user } = renderPage();
    const table = await screen.findByRole("table");
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows[0]).toHaveTextContent("GPT-4.1");
    expect(rows[0]).toHaveTextContent("成功");
    expect(rows[1]).toHaveTextContent("失败");
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument();

    await user.click(within(rows[1]).getByRole("button", { name: /展开|核对/ }));
    expect(await screen.findByText("timeout")).toBeInTheDocument();
    expect(screen.getByText(/重试/)).toHaveTextContent("1");
    expect(screen.getByText("upstream request timed out")).toBeInTheDocument();
  });
});

describe("TC-047 失败详情无密钥", () => {
  test("TC-047 展开失败行显示错误与重试次数且不含密钥", async () => {
    const api = installFetchMock();
    mockCommon(api);
    api.on("GET", "/api/v1/calls", () =>
      jsonResponse({ items: [failedCall], nextCursor: null }),
    );
    api.on("GET", "/api/v1/calls/17", () =>
      jsonResponse({ ...failedCall, resultText: null }),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /展开|核对/ }));
    expect(await screen.findByText("timeout")).toBeInTheDocument();
    expect(screen.getByText(/重试/)).toHaveTextContent("1");
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument();
  });
});

describe("TC-048 无匹配空态不是错误", () => {
  test("TC-048 筛选无匹配展示空态而不是错误", async () => {
    const api = installFetchMock();
    mockCommon(api);
    api.on("GET", "/api/v1/calls", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    const { user } = renderPage();
    expect(await screen.findByText(/还没有调用记录/)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("状态"), "failed");
    expect(
      await screen.findByText(/没有符合筛选条件的调用记录/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
