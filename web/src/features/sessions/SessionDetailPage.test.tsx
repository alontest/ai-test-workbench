import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { SessionDetailPage } from "./SessionDetailPage";
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

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const api = installFetchMock();
  api.on("GET", "/api/v1/sessions/42", () => jsonResponse(session));
  api.on("GET", "/api/v1/sessions/42/events", () =>
    jsonResponse({ items: [], nextCursor: null }),
  );
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

describe("TC-028 会话详情 Tab 面板切换", () => {
  test("TC-028 默认展示文本面板，切换后隐藏非激活面板，切回保留草稿", async () => {
    const { user } = renderPage();
    await screen.findByRole("heading", { name: "订单超时排查" });

    const textPanel = screen.getByRole("tabpanel", { name: "文本粘贴" });
    const uploadPanel = screen.getByRole("tabpanel", { name: "文件上传" });
    const callPanel = screen.getByRole("tabpanel", { name: "调用" });
    expect(screen.getAllByRole("tabpanel")).toHaveLength(3);
    expect(textPanel).toHaveAttribute("data-state", "active");
    expect(uploadPanel).toHaveAttribute("data-state", "inactive");
    expect(callPanel).toHaveAttribute("data-state", "inactive");

    await user.type(screen.getByLabelText(/正文/), "先写下这段草稿");

    await user.click(screen.getByRole("tab", { name: "文件上传" }));
    expect(uploadPanel).toHaveAttribute("data-state", "active");
    expect(textPanel).toHaveAttribute("data-state", "inactive");

    await user.click(screen.getByRole("tab", { name: "调用" }));
    expect(callPanel).toHaveAttribute("data-state", "active");
    expect(uploadPanel).toHaveAttribute("data-state", "inactive");
    await user.type(screen.getByLabelText(/提示/), "再写一段调用提示");

    await user.click(screen.getByRole("tab", { name: "文本粘贴" }));
    expect(screen.getByLabelText(/正文/)).toHaveValue("先写下这段草稿");
    expect(screen.getByLabelText(/提示/)).toHaveValue("再写一段调用提示");
  });
});
