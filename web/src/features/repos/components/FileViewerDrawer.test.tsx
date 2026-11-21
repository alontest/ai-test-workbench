import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { FileViewerDrawer } from "./FileViewerDrawer";

const FILE_PATH = "/api/v1/repo-bindings/b1/file";

function Harness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        打开文件
      </button>
      <FileViewerDrawer
        bindingId="b1"
        open={open}
        target={{ repoId: "pay/checkout", ref: "main", path: "src/main.py" }}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

describe("TC-250 文件抽屉错误态", () => {
  test.each<[number, string, RegExp]>([
    [413, "repo_file_too_large", /超过 1 MiB 上限/],
    [415, "repo_file_binary", /二进制内容/],
    [422, "repo_file_not_utf8", /UTF-8/],
    [400, "invalid_path", /路径不合法/],
  ])("TC-250 HTTP %s (%s) 渲染可读错误", async (status, code, pattern) => {
    const api = installFetchMock();
    api.on("GET", FILE_PATH, () =>
      jsonResponse(
        {
          code,
          message: "读取被拒绝。",
          details:
            code === "repo_file_too_large"
              ? [
                  {
                    field: "sizeBytes",
                    message: "实际 3565158 字节，上限 1048576 字节",
                  },
                ]
              : [],
          requestId: "t-file",
        },
        status,
      ),
    );
    const user = userEvent.setup();
    renderWithApp(<Harness />);
    await user.click(screen.getByRole("button", { name: "打开文件" }));
    expect(await screen.findByTestId("file-error")).toBeInTheDocument();
    expect(screen.getByText(pattern)).toBeInTheDocument();
  });

  test("TC-250 文本内容按纯文本渲染，Esc 关闭并把焦点还给触发元素", async () => {
    const api = installFetchMock();
    api.on("GET", FILE_PATH, () =>
      jsonResponse({
        path: "src/main.py",
        ref: "main",
        sizeBytes: 12,
        encoding: "text",
        content: "print('hi')\n",
        fetchedAt: "2026-11-20T02:30:00Z",
      }),
    );
    const user = userEvent.setup();
    renderWithApp(<Harness />);
    const trigger = screen.getByRole("button", { name: "打开文件" });
    trigger.focus();
    await user.click(trigger);

    const drawer = await screen.findByRole("dialog");
    await waitFor(() => expect(drawer).toHaveFocus());
    const content = await screen.findByTestId("file-content");
    expect(content.tagName).toBe("PRE");
    expect(content).toHaveTextContent("print('hi')");

    await user.keyboard("{Escape}");
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(),
    );
    expect(trigger).toHaveFocus();
  });
});
