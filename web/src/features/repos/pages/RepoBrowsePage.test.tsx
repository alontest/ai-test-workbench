import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import {
  baselineFixture,
  bindingFixture,
  branchFixture,
  commitFixture,
} from "../test-fixtures";
import { RepoBrowsePage } from "./RepoBrowsePage";

function renderBrowsePage() {
  return renderWithApp(<div />, {
    route: "/projects/1/repos/b1",
    routes: (
      <Routes>
        <Route
          path="/projects/:projectId/repos/:bindingId"
          element={<RepoBrowsePage />}
        />
      </Routes>
    ),
  });
}

describe("TC-250 仓库浏览页只读态", () => {
  test("TC-250 已解绑时选择器与树行 aria-disabled 且不发实时请求", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/repo-bindings/b1", () =>
      jsonResponse(
        bindingFixture({
          status: "revoked",
          revokedAt: "2026-11-21T01:00:00Z",
          tokenMasked: "",
        }),
      ),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/baseline", () =>
      jsonResponse(
        baselineFixture({
          status: "revoked",
          revoked: true,
        }),
      ),
    );

    renderBrowsePage();

    expect(await screen.findByTestId("revoked-notice")).toBeInTheDocument();
    expect(await screen.findByText("release/4.2")).toBeInTheDocument();
    expect(
      screen.getByText("fix(pay): 回调签名校验顺序调整"),
    ).toBeInTheDocument();

    expect(screen.getByLabelText("检索仓库")).toBeDisabled();
    expect(screen.getByLabelText("选择仓库")).toBeDisabled();
    expect(screen.getByLabelText("分支（实时，分页）")).toBeDisabled();
    expect(screen.getByRole("button", { name: "刷新" })).toBeDisabled();

    const urls = api.fetch.mock.calls.map(([input]) => String(input));
    for (const live of ["/repositories", "/branches", "/commits", "/tree"]) {
      expect(urls.some((url) => url.includes(live))).toBe(false);
    }
  });

  test("TC-250 从未同步时返回空态而不是错误页", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/repo-bindings/b1", () => jsonResponse(bindingFixture()));
    api.on("GET", "/api/v1/repo-bindings/b1/baseline", () =>
      jsonResponse(
        baselineFixture({
          metadataSynced: false,
          repo: null,
          branches: [],
          commits: [],
          lastSyncSuccessAt: null,
          fetchedAt: null,
          guide: "sync_first",
        }),
      ),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/repositories", () =>
      jsonResponse({
        metadataSynced: false,
        live: false,
        items: [],
        nextCursor: null,
        total: null,
        guide: "sync_first",
      }),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/branches", () =>
      jsonResponse({
        metadataSynced: false,
        live: false,
        items: [],
        nextCursor: null,
        total: null,
        guide: "sync_first",
      }),
    );

    renderBrowsePage();
    expect(
      await screen.findByText("还没有可浏览的元数据"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "去同步" })).toBeInTheDocument();
  });

  test("TC-250 正常绑定加载仓库、分支、提交与目录树", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/repo-bindings/b1", () => jsonResponse(bindingFixture()));
    api.on("GET", "/api/v1/repo-bindings/b1/baseline", () =>
      jsonResponse(baselineFixture()),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/repositories", () =>
      jsonResponse({
        metadataSynced: true,
        live: true,
        items: [
          {
            repoId: "pay/checkout",
            fullName: "pay/checkout",
            displayName: "pay/checkout",
            defaultBranch: "main",
            webUrl: "https://github.com/pay/checkout",
          },
        ],
        nextCursor: null,
        total: 1,
        guide: null,
      }),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/branches", () =>
      jsonResponse({
        metadataSynced: true,
        live: true,
        items: [branchFixture()],
        nextCursor: null,
        total: 1,
        guide: null,
      }),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/commits", () =>
      jsonResponse({
        metadataSynced: true,
        live: true,
        items: [commitFixture()],
        nextCursor: null,
        total: 1,
        guide: null,
      }),
    );
    api.on("GET", "/api/v1/repo-bindings/b1/tree", () =>
      jsonResponse({
        metadataSynced: true,
        live: true,
        path: "",
        ref: "main",
        items: [
          {
            name: "README.md",
            path: "README.md",
            type: "file",
            sizeBytes: 1200,
          },
        ],
        truncated: false,
        hasMore: false,
        nextCursor: null,
        total: 1,
        guide: null,
      }),
    );

    renderBrowsePage();
    expect(await screen.findByText("README.md")).toBeInTheDocument();
    expect(
      screen.getByText("fix(pay): 回调签名校验顺序调整"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("选择仓库")).toHaveValue("pay/checkout");
    expect(screen.getByLabelText("分支（实时，分页）")).toHaveValue("main");
  });
});
