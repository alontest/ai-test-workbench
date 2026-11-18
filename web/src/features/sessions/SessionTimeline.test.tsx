import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { SessionDetailPage } from "./SessionDetailPage";
import type { SessionSummary } from "./types";

function sessionFixture(
  overrides: Partial<SessionSummary> = {},
): SessionSummary {
  return {
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
    ...overrides,
  };
}

const LONG_INPUT = "第一行预览\n第二行预览\n第三行预览\nUNIQUE_FULL_LINE";

function eventsPage(nextCursor: string | null = null) {
  return {
    items: [
      {
        eventId: 1,
        sessionId: 42,
        type: "input_text",
        payload: {
          title: "报错日志",
          text: LONG_INPUT,
          charCount: LONG_INPUT.length,
        },
        createdAt: "2026-11-18T02:01:00Z",
      },
      {
        eventId: 2,
        sessionId: 42,
        type: "call",
        payload: {
          callId: 17,
          modelId: 3,
          modelDisplayName: "GPT-4.1",
          status: "success",
          latencyMs: 8400,
          retryCount: 0,
          promptPreview: "请分析以下登录报错",
          errorCode: null,
        },
        createdAt: "2026-11-18T02:03:00Z",
      },
      {
        eventId: 3,
        sessionId: 42,
        type: "artifact",
        payload: {
          artifactId: 9,
          fileName: "app.log",
          byteSize: 12400,
          mimeType: "text/plain",
          kind: "upload",
        },
        createdAt: "2026-11-18T02:04:00Z",
      },
      {
        eventId: 4,
        sessionId: 42,
        type: "call",
        payload: {
          callId: 18,
          modelId: 3,
          modelDisplayName: "GPT-4.1",
          status: "failed",
          latencyMs: 120000,
          retryCount: 1,
          promptPreview: "请分析脱敏后的摘要",
          errorCode: "ai_auth",
        },
        createdAt: "2026-11-18T02:05:00Z",
      },
      {
        eventId: 5,
        sessionId: 42,
        type: "status_change",
        payload: {
          from: "in_progress",
          to: "completed",
          actor: "local-user",
          at: "2026-11-18T02:06:00Z",
          reason: null,
        },
        createdAt: "2026-11-18T02:06:00Z",
      },
    ],
    nextCursor,
  };
}

function renderPage(status: SessionSummary["status"] = "in_progress") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const api = installFetchMock();
  api.on("GET", "/api/v1/sessions/42", () =>
    jsonResponse(
      sessionFixture({
        status,
        closedAt: status === "in_progress" ? null : "2026-11-18T02:06:00Z",
      }),
    ),
  );
  api.on("GET", "/api/v1/sessions/42/events", (_request, url) => {
    const cursor = url.searchParams.get("cursor");
    if (cursor) {
      return jsonResponse({
        items: [
          {
            eventId: 6,
            sessionId: 42,
            type: "input_text",
            payload: { title: "下一页", text: "page-two", charCount: 8 },
            createdAt: "2026-11-18T02:07:00Z",
          },
        ],
        nextCursor: null,
      });
    }
    return jsonResponse(eventsPage("cursor-2"));
  });
  return {
    user: userEvent.setup(),
    api,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/sessions/42"]}>
          <Routes>
            <Route path="/sessions/:id" element={<SessionDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-028 时间线按发生顺序渲染四类事件", () => {
  test("TC-028 四类事件按 eventId 升序展示且输入可展开全文", async () => {
    const { user } = renderPage();
    expect(await screen.findByText("报错日志")).toBeInTheDocument();
    expect(screen.getByText("app.log")).toBeInTheDocument();
    expect(screen.getByText(/状态变更|已完成/)).toBeInTheDocument();

    const titles = screen
      .getAllByRole("article")
      .map((node) => node.getAttribute("data-event-type"));
    expect(titles).toEqual([
      "input_text",
      "call",
      "artifact",
      "call",
      "status_change",
    ]);

    expect(screen.queryByText("UNIQUE_FULL_LINE")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /展开全文/ }));
    expect(screen.getByText("UNIQUE_FULL_LINE")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /收起/ }));
    expect(screen.queryByText("UNIQUE_FULL_LINE")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /加载更多/ }));
    expect(await screen.findByText("下一页")).toBeInTheDocument();
  });
});

describe("TC-044 调用卡展示摘要且无密钥", () => {
  test("TC-044 成功与失败调用卡含模型/耗时/状态/摘要，失败含重试，不含密钥", async () => {
    renderPage();
    const articles = await screen.findAllByRole("article");
    const success = articles.find(
      (node) => node.getAttribute("data-event-type") === "call",
    );
    expect(success).toBeTruthy();
    expect(within(success!).getByText("GPT-4.1")).toBeInTheDocument();
    expect(within(success!).getByText(/成功/)).toBeInTheDocument();
    expect(within(success!).getByText(/8\.4|8400|8,400/)).toBeInTheDocument();
    expect(within(success!).getByText(/请分析以下登录报错/)).toBeInTheDocument();

    const failed = articles.filter(
      (node) => node.getAttribute("data-event-type") === "call",
    )[1];
    expect(within(failed).getByText(/失败/)).toBeInTheDocument();
    expect(within(failed).getByText(/重试\s*1/)).toBeInTheDocument();
    expect(within(failed).getByText(/ai_auth/)).toBeInTheDocument();
    expect(screen.queryByText(/sk-very-secret/)).not.toBeInTheDocument();
  });

  test("TC-044 终态会话时间线只读且提示不再接受新输入", async () => {
    renderPage("completed");
    expect(await screen.findByText(/会话已结束，不再接受新输入/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /添加到时间线/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: /发起调用/ })).toBeDisabled();
  });
});

describe("TC-029 标记完成", () => {
  const statusEvent = {
    eventId: 9,
    sessionId: 42,
    type: "status_change",
    payload: {
      from: "in_progress",
      to: "completed",
      actor: "local-user",
      at: "2026-11-18T02:09:00Z",
      reason: null,
    },
    createdAt: "2026-11-18T02:09:00Z",
  };

  function renderCompletablePage() {
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const api = installFetchMock();
    let completed = false;
    api.on("GET", "/api/v1/sessions/42", () =>
      jsonResponse(
        sessionFixture({
          status: completed ? "completed" : "in_progress",
          closedAt: completed ? "2026-11-18T02:09:00Z" : null,
        }),
      ),
    );
    api.on("GET", "/api/v1/sessions/42/events", () =>
      jsonResponse({
        items: completed ? [statusEvent] : eventsPage().items,
        nextCursor: null,
      }),
    );
    api.on("POST", "/api/v1/sessions/42/complete", () => {
      completed = true;
      return jsonResponse(
        sessionFixture({
          status: "completed",
          closedAt: "2026-11-18T02:09:00Z",
        }),
      );
    });
    return {
      user: userEvent.setup(),
      api,
      ...render(
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={["/sessions/42"]}>
            <Routes>
              <Route path="/sessions/:id" element={<SessionDetailPage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>,
      ),
    };
  }

  test("TC-029 仅进行中可见，二次确认后完成并转只读、时间线记录状态变更", async () => {
    const { user } = renderCompletablePage();
    const trigger = await screen.findByRole("button", { name: "标记完成" });
    await user.click(trigger);

    expect(await screen.findByRole("alertdialog")).toHaveTextContent(/标记完成/);
    await user.click(screen.getByRole("button", { name: "确认完成" }));

    expect(
      await screen.findByText(/会话已结束，不再接受新输入/),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "标记完成" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "删除会话" })).not.toBeDisabled();

    const statusArticle = (await screen.findAllByRole("article")).find(
      (node) => node.getAttribute("data-event-type") === "status_change",
    );
    expect(statusArticle).toBeTruthy();
    expect(within(statusArticle!).getByText(/已完成/)).toBeInTheDocument();
  });

  test("TC-029 取消确认不调用完成接口", async () => {
    const { user, api } = renderCompletablePage();
    await user.click(await screen.findByRole("button", { name: "标记完成" }));
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "取消" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();

    const posted = api.fetch.mock.calls.filter((call) => {
      const init = call[1] as RequestInit | undefined;
      return init?.method === "POST";
    });
    expect(posted).toHaveLength(0);
  });

  test.each(["completed", "failed"] as const)(
    "TC-029 %s 会话不提供标记完成",
    async (status) => {
      renderPage(status);
      expect(
        await screen.findByText(/会话已结束，不再接受新输入/),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "标记完成" }),
      ).not.toBeInTheDocument();
    },
  );
});
