import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import type { RepoTestResult } from "../api/types";
import { bindingFixture } from "../test-fixtures";
import { RepoBindingForm } from "./RepoBindingForm";
import { UpdateTokenForm } from "./UpdateTokenForm";

const TEST_CONNECTION_PATH = "/api/v1/repo-bindings/test-connection";

function mockTestResult(mode: RepoTestResult) {
  const api = installFetchMock();
  api.on("POST", TEST_CONNECTION_PATH, () =>
    jsonResponse({
      result: mode,
      testedAt: "2026-11-20T02:10:00Z",
      message: mode === "success" ? "连接成功。" : "只读请求失败。",
      defaultBranch: "main",
      latestCommitAt: null,
      retryAfterAt: null,
      bindingStatus: null,
    }),
  );
  return api;
}

async function fillAndTest(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "GitHub" }));
  await user.type(screen.getByLabelText(/仓库标识/), "owner/repo");
  await user.type(screen.getByLabelText(/访问令牌/), "ghp_test_token");
  await user.click(screen.getByRole("button", { name: "测试连接" }));
}

describe("TC-250 保存前测试四类结果", () => {
  test.each<[RepoTestResult, string]>([
    ["success", "连接成功"],
    ["auth-error", "鉴权失败"],
    ["unreachable", "网络不可达"],
    ["permission-denied", "权限不足"],
  ])("TC-250 %s 渲染为「%s」且不误归类", async (mode, label) => {
    mockTestResult(mode);
    const user = userEvent.setup();
    renderWithApp(
      <RepoBindingForm
        projectId={1}
        open
        onClose={() => undefined}
        onSaved={() => undefined}
      />,
    );
    await fillAndTest(user);
    expect(await screen.findByText(label)).toBeInTheDocument();
  });

  test("TC-250 字段变更后上一次结果置灰并标「已失效（时间 · 结果）」", async () => {
    mockTestResult("success");
    const user = userEvent.setup();
    renderWithApp(
      <RepoBindingForm
        projectId={1}
        open
        onClose={() => undefined}
        onSaved={() => undefined}
      />,
    );
    await fillAndTest(user);
    expect(await screen.findByText("连接成功")).toBeInTheDocument();

    await user.type(screen.getByLabelText(/仓库标识/), "x");
    const stale = screen.getByText(/已失效（/);
    expect(stale).toHaveTextContent("已失效（2026-11-20 02:10 UTC · 连接成功）");
    expect(
      screen.getByText(/表单字段已修改，请重新测试/),
    ).toBeInTheDocument();
  });

  test("TC-250 云效未填组织 ID 时就近提示且不发请求", async () => {
    const api = installFetchMock();
    const user = userEvent.setup();
    renderWithApp(
      <RepoBindingForm
        projectId={1}
        open
        onClose={() => undefined}
        onSaved={() => undefined}
      />,
    );
    await user.type(screen.getByLabelText(/仓库标识/), "pay-group/pay-api");
    await user.type(screen.getByLabelText(/访问令牌/), "ghp_test_token");
    await user.click(screen.getByRole("button", { name: "测试连接" }));
    expect(await screen.findByText("云效需要组织 ID。")).toBeInTheDocument();
    expect(
      api.fetch.mock.calls.some(([input]) =>
        String(input).includes("test-connection"),
      ),
    ).toBe(false);
  });

  test("TC-250 令牌与测试结果不写入 localStorage / sessionStorage", async () => {
    mockTestResult("success");
    const user = userEvent.setup();
    renderWithApp(
      <RepoBindingForm
        projectId={1}
        open
        onClose={() => undefined}
        onSaved={() => undefined}
      />,
    );
    await fillAndTest(user);
    await screen.findByText("连接成功");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("TC-250 令牌只显示掩码", () => {
  test("TC-250 更新令牌表单回显掩码、输入为空且为口令类型", () => {
    const binding = bindingFixture();
    renderWithApp(
      <UpdateTokenForm
        binding={binding}
        open
        onClose={() => undefined}
        onSaved={() => undefined}
      />,
    );
    expect(screen.getByText("ghp_****abcd")).toBeInTheDocument();
    const input = screen.getByLabelText("访问令牌");
    expect(input).toHaveValue("");
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute(
      "placeholder",
      "留空表示不修改（当前 ghp_****abcd）",
    );
  });
});
