import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { KnowledgeBaseListPage } from "./KnowledgeBaseListPage";

const base = {
  projectId: 1,
  current: true,
  status: "ready",
  fileCount: 3,
  totalByteSize: 1024,
  supersededCount: 0,
  createdAt: "2026-11-18T02:30:00Z",
  project: { id: 1, name: "支付台" },
};

const first = {
  ...base,
  kbId: "1".repeat(32),
  name: "支付域知识库",
  version: 2,
  generatedAt: "2026-11-17T09:12:00Z",
  entryCount: 42,
  latestKbId: "1".repeat(32),
  supersededCount: 1,
};

const second = {
  ...base,
  kbId: "2".repeat(32),
  name: "风控术语库",
  version: 1,
  generatedAt: null,
  entryCount: 18,
  latestKbId: "2".repeat(32),
};

const third = {
  ...base,
  kbId: "3".repeat(32),
  name: "第三库",
  version: 1,
  generatedAt: null,
  entryCount: 5,
  latestKbId: "3".repeat(32),
};

function renderPage() {
  const api = installFetchMock();
  api.on("GET", "/api/v1/projects", () =>
    jsonResponse({
      items: [{ projectId: 1, name: "支付台" }],
      nextCursor: null,
    }),
  );
  api.on("GET", "/api/v1/knowledge-bases", (_request, url) => {
    if (url.searchParams.get("cursor") === "next") {
      return jsonResponse({ items: [third], nextCursor: null });
    }
    return jsonResponse({ items: [first, second], nextCursor: "next" });
  });
  return {
    api,
    user: userEvent.setup(),
    ...renderWithApp(<KnowledgeBaseListPage />),
  };
}

describe("KB-016 知识库列表", () => {
  test("列出当前版本、生成时间缺失显示未知与旧版本提示", async () => {
    renderPage();
    expect(await screen.findByText("支付域知识库")).toBeInTheDocument();
    expect(screen.getByText("风控术语库")).toBeInTheDocument();
    expect(screen.getAllByText("未知").length).toBeGreaterThan(0);
    expect(
      screen.getByText(/另有 1 个旧版本（只读）/),
    ).toBeInTheDocument();
    expect(screen.getByText("共 2 个知识库（可分页加载）")).toBeInTheDocument();
  });

  test("加载更多按游标追加下一批条目", async () => {
    const { user } = renderPage();
    expect(await screen.findByText("支付域知识库")).toBeInTheDocument();
    expect(screen.queryByText("第三库")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "加载更多" }));
    expect(await screen.findByText("第三库")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "加载更多" })).not.toBeInTheDocument();
  });

  test("删除需要二次确认后才请求 DELETE", async () => {
    const { api, user } = renderPage();
    await screen.findByText("支付域知识库");
    const deleteButtons = screen.getAllByRole("button", { name: "删除" });
    await user.click(deleteButtons[0]);
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent("删除后不可恢复");
    expect(dialog).toHaveTextContent("历史会话与调用记录不变");
    api.on(
      "DELETE",
      `/api/v1/knowledge-bases/${first.kbId}`,
      () => new Response(null, { status: 204 }),
    );
    await user.click(within(dialog).getByRole("button", { name: "删除" }));
    expect(
      api.fetch.mock.calls.some(([, init]) => init?.method === "DELETE"),
    ).toBe(true);
  });
});
