import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, test, vi } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { RepoTree } from "./RepoTree";
import { TreeNode } from "./TreeNode";

const TREE_PATH = "/api/v1/repo-bindings/b1/tree";

function treePage(overrides: Record<string, unknown> = {}) {
  return {
    metadataSynced: true,
    live: true,
    path: "",
    ref: "main",
    items: [
      { name: "src", path: "src", type: "dir", sizeBytes: null },
      { name: "README.md", path: "README.md", type: "file", sizeBytes: 1200 },
    ],
    truncated: false,
    hasMore: false,
    nextCursor: null,
    total: 2,
    guide: null,
    ...overrides,
  };
}

function renderTree(props: Partial<ComponentProps<typeof RepoTree>> = {}) {
  return renderWithApp(
    <RepoTree
      bindingId="b1"
      repoId="pay/checkout"
      ref="main"
      onOpenFile={() => undefined}
      {...props}
    />,
  );
}

describe("TC-250 目录树 truncated 与 hasMore", () => {
  test("TC-250 truncated 显示固定提示且不冒充 hasMore", async () => {
    const api = installFetchMock();
    api.on("GET", TREE_PATH, () => jsonResponse(treePage({ truncated: true })));
    renderTree();
    expect(await screen.findByText("src/")).toBeInTheDocument();
    expect(
      screen.getByText("目录树不完整，请逐级浏览"),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "加载下一页" }),
    ).not.toBeInTheDocument();
  });

  test("TC-250 hasMore 显示加载下一页且不冒充 truncated", async () => {
    const api = installFetchMock();
    api.on("GET", TREE_PATH, () =>
      jsonResponse(
        treePage({ hasMore: true, nextCursor: "cursor-1", items: [] }),
      ),
    );
    renderTree();
    expect(
      await screen.findByRole("button", { name: "加载下一页" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("目录树不完整，请逐级浏览"),
    ).not.toBeInTheDocument();
  });

  test("TC-250 已解绑时目录树置灰且不发请求", async () => {
    const api = installFetchMock();
    renderTree({ disabled: true });
    expect(
      await screen.findByText(/已解绑：目录树入口置灰/),
    ).toBeInTheDocument();
    expect(
      api.fetch.mock.calls.some(([input]) => String(input).includes("/tree")),
    ).toBe(false);
  });
});

describe("TC-250 已解绑树行 aria-disabled 且点击不发请求", () => {
  test("TC-250 文件行与目录行均标记 aria-disabled 并忽略点击", async () => {
    const onOpen = vi.fn();
    const onToggle = vi.fn();
    const user = userEvent.setup();
    const { rerender } = render(
      <TreeNode
        entry={{
          name: "README.md",
          path: "README.md",
          type: "file",
          sizeBytes: 10,
        }}
        depth={0}
        expanded={false}
        disabled
        onToggle={onToggle}
        onOpen={onOpen}
      />,
    );
    const fileRow = screen.getByRole("button", { name: /README\.md/ });
    expect(fileRow).toHaveAttribute("aria-disabled", "true");
    await user.click(fileRow);
    expect(onOpen).not.toHaveBeenCalled();

    rerender(
      <TreeNode
        entry={{ name: "src", path: "src", type: "dir", sizeBytes: null }}
        depth={1}
        expanded={false}
        disabled
        onToggle={onToggle}
        onOpen={onOpen}
      />,
    );
    const dirRow = screen.getByRole("button", { name: /src\// });
    expect(dirRow).toHaveAttribute("aria-disabled", "true");
    await user.click(dirRow);
    expect(onToggle).not.toHaveBeenCalled();
  });
});
