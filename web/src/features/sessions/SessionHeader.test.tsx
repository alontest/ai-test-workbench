import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { SessionHeader } from "./SessionHeader";
import type { SessionSummary } from "./types";

const session: SessionSummary = {
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
};

function renderHeader() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/sessions/42"]}>
          <Routes>
            <Route path="/sessions/:id" element={<SessionHeader session={session} />} />
            <Route path="/sessions" element={<p>会话列表</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-030 删除会话确认级联范围", () => {
  test("TC-030 确认弹窗列出级联范围且取消不删除", async () => {
    const api = installFetchMock();
    api.on("DELETE", "/api/v1/sessions/42", () => jsonResponse(null, 204));
    const { user } = renderHeader();
    await user.click(screen.getByRole("button", { name: "删除会话" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent(/事件/);
    expect(dialog).toHaveTextContent(/制品|sessions\/42/);
    expect(dialog).toHaveTextContent(/调用记录/);
    await user.click(screen.getByRole("button", { name: "取消" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    const deleted = api.fetch.mock.calls.filter((call) => {
      const init = call[1] as RequestInit | undefined;
      return init?.method === "DELETE";
    });
    expect(deleted).toHaveLength(0);
  });

  test("TC-030 确认删除后回到列表", async () => {
    const api = installFetchMock();
    api.on("DELETE", "/api/v1/sessions/42", () => new Response(null, { status: 204 }));
    const { user } = renderHeader();
    await user.click(screen.getByRole("button", { name: "删除会话" }));
    await user.click(await screen.findByRole("button", { name: "删除" }));
    expect(await screen.findByText("会话列表")).toBeInTheDocument();
  });
});
