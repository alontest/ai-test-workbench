import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { bindingFixture } from "../test-fixtures";
import { SyncControl } from "./SyncControl";
import { SyncRecordTable } from "./SyncRecordTable";
import { UnbindDialog } from "./UnbindDialog";

describe("TC-250 同步记录与解绑确认", () => {
  test("TC-250 失败记录说明保留上次基线与限流时间", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/repo-bindings/b1/sync-records", () =>
      jsonResponse({
        items: [
          {
            syncId: "s".repeat(32),
            bindingId: "b1",
            startedAt: "2026-11-20T02:40:00Z",
            finishedAt: "2026-11-20T02:40:01Z",
            status: "failed",
            durationMs: 1200,
            repoCount: null,
            branchCount: null,
            commitCount: null,
            errorCategory: "rate_limit",
            errorMessage: "供应商限流",
            retryAfterAt: "2026-11-20T03:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    const user = userEvent.setup();
    renderWithApp(<SyncRecordTable bindingId="b1" />);
    await user.click(screen.getByRole("button", { name: "查看同步记录" }));
    expect(await screen.findByText(/限流至/)).toBeInTheDocument();
    expect(
      screen.getByText(/保留上次成功基线与时间/),
    ).toBeInTheDocument();
    expect(screen.getByText("失败")).toBeInTheDocument();
  });

  test("TC-250 同步中禁用按钮并显示「同步中…」", () => {
    renderWithApp(
      <SyncControl
        binding={bindingFixture()}
        syncing
        onSync={() => undefined}
      />,
    );
    expect(screen.getByRole("button", { name: "同步中…" })).toBeDisabled();
    expect(screen.getByText(/上次同步/)).toBeInTheDocument();
  });

  test("TC-250 同步失败横幅保留上次成功时间", () => {
    renderWithApp(
      <SyncControl
        binding={bindingFixture({
          lastSyncStatus: "failed",
          lastSyncErrorCategory: "network",
          lastSyncErrorMessage: "供应商不可达",
        })}
        syncing={false}
        onSync={() => undefined}
      />,
    );
    expect(screen.getByText(/同步失败/)).toBeInTheDocument();
    expect(screen.getByText(/保留上次成功基线与时间/)).toBeInTheDocument();
    expect(
      screen.getAllByText(/2026-11-20 02:20 UTC/).length,
    ).toBeGreaterThan(0);
  });

  test("TC-250 解绑对话框列出五条后果", async () => {
    renderWithApp(
      <UnbindDialog
        open
        binding={bindingFixture()}
        onConfirm={() => undefined}
        onCancel={() => undefined}
      />,
    );
    expect(await screen.findByText("撤销仓库绑定？")).toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(
      screen.getByText(/重新绑定同一仓库会生成新的 bindingId/),
    ).toBeInTheDocument();
  });
});
