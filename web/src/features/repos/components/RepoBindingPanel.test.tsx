import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { bindingFixture } from "../test-fixtures";
import { RepoBindingPanel } from "./RepoBindingPanel";
import { RepoStatusBadge, type RepoStatus } from "./RepoStatusBadge";

describe("TC-250 绑定面板状态与权限说明", () => {
  test("TC-250 四态徽标同时展示文字与状态", () => {
    const cases: Array<{ status: RepoStatus; label: string }> = [
      { status: "unverified", label: "未验证" },
      { status: "connected", label: "已连接" },
      { status: "token_invalid", label: "令牌失效" },
      { status: "revoked", label: "已解绑" },
      { status: "syncing", label: "同步中" },
    ];
    for (const item of cases) {
      const { unmount } = renderWithApp(<RepoStatusBadge status={item.status} />);
      expect(screen.getByText(item.label)).toBeInTheDocument();
      const badge = screen
        .getByText(item.label)
        .closest("[data-status]") as HTMLElement;
      expect(badge).toHaveAttribute("data-status", item.status);
      unmount();
    }
  });

  test("TC-250 面板展示掩码、单一失效横幅与已解绑只读行", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects/1/repo-bindings", () =>
      jsonResponse({
        items: [
          bindingFixture(),
          bindingFixture({
            bindingId: "b".repeat(32),
            repoName: "pay/docs",
            tokenMasked: "ghp_****efgh",
            status: "token_invalid",
          }),
          bindingFixture({
            bindingId: "c".repeat(32),
            repoName: "pay/legacy",
            tokenMasked: "",
            status: "revoked",
            revokedAt: "2026-11-21T01:00:00Z",
            lastSyncSuccessAt: "2026-11-19T01:00:00Z",
          }),
        ],
        nextCursor: null,
      }),
    );
    renderWithApp(<RepoBindingPanel projectId={1} />);

    const mount = await screen.findByTestId("repo-binding-panel");
    expect(mount).toHaveAttribute("data-mount", "repo-binding-panel");
    expect(await screen.findByText("ghp_****abcd")).toBeInTheDocument();
    expect(screen.getByText("已连接")).toBeInTheDocument();
    expect(screen.getByText("令牌失效")).toBeInTheDocument();
    expect(screen.getByText("已解绑")).toBeInTheDocument();

    expect(screen.getAllByTestId("token-invalid-banner")).toHaveLength(1);
    expect(screen.getAllByTestId("binding-row")).toHaveLength(3);

    const rows = screen.getAllByTestId("binding-row");
    const revokedRow = rows.find((row) => row.textContent?.includes("pay/legacy"));
    expect(revokedRow).toBeDefined();
    expect(
      within(revokedRow as HTMLElement).getByText(/令牌 —/),
    ).toBeInTheDocument();
    expect(
      within(revokedRow as HTMLElement).queryByRole("button", { name: "更新令牌" }),
    ).not.toBeInTheDocument();

    expect(screen.getAllByRole("button", { name: "同步" })).toHaveLength(2);
    expect(
      within(revokedRow as HTMLElement).queryByRole("button", { name: "同步" }),
    ).not.toBeInTheDocument();
    expect(screen.getAllByText(/从未测试|上次测试/).length).toBeGreaterThan(0);
  });

  test("TC-250 未选择项目时不发请求并渲染空态", async () => {
    const api = installFetchMock();
    renderWithApp(<RepoBindingPanel projectId={null} />);
    expect(await screen.findByText("先选择一个项目")).toBeInTheDocument();
    expect(
      api.fetch.mock.calls.some(([input]) =>
        String(input).includes("/repo-bindings"),
      ),
    ).toBe(false);
  });

  test("TC-250 添加表单显示只读最小权限说明且令牌为口令输入", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects/1/repo-bindings", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    const user = userEvent.setup();
    renderWithApp(<RepoBindingPanel projectId={1} />);
    expect(await screen.findByText("还没有绑定仓库")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /添加绑定/ }));
    expect(screen.getByText(/建议只读最小权限/)).toBeInTheDocument();
    expect(screen.getByLabelText(/访问令牌/)).toHaveAttribute(
      "type",
      "password",
    );
  });
});
