import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test, vi } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { LoginPage } from "./LoginPage";

function renderLogin(route = "/login") {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    fetch: undefined as ReturnType<typeof installFetchMock> | undefined,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/sessions" element={<div>会话页</div>} />
            <Route path="/" element={<div>首页</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-001 登录页状态机", () => {
  test("TC-001 默认态展示口令输入与提交且无业务字段", () => {
    renderLogin();
    expect(screen.getByLabelText(/口令/)).toHaveAttribute("type", "password");
    expect(screen.getByRole("button", { name: /登录/ })).toBeEnabled();
    expect(screen.queryByRole("link", { name: /项目/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/项目上下文/)).not.toBeInTheDocument();
  });

  test("TC-001 错误口令进入 error 态并展示统一错误", async () => {
    const api = installFetchMock();
    api.on("POST", "/api/v1/auth/login", () =>
      jsonResponse(
        {
          code: "login_failed",
          message: "口令错误，请重试。",
          details: [],
          requestId: "t-err",
        },
        401,
      ),
    );
    const { user } = renderLogin();
    await user.type(screen.getByLabelText(/口令/), "wrong");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    expect(await screen.findByText(/口令错误/)).toBeInTheDocument();
  });

  test("TC-001 提交中进入 submitting 并禁用按钮", async () => {
    const api = installFetchMock();
    let resolveLogin: ((value: Response) => void) | undefined;
    api.on(
      "POST",
      "/api/v1/auth/login",
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        }),
    );
    const { user } = renderLogin();
    await user.type(screen.getByLabelText(/口令/), "secret");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    expect(screen.getByRole("button", { name: /登录/ })).toBeDisabled();
    resolveLogin?.(jsonResponse({ authenticated: true }));
    await waitFor(() => {
      expect(screen.getByText("首页")).toBeInTheDocument();
    });
  });
});

describe("TC-008 登录不把令牌写入 JS 可读存储", () => {
  test("TC-008 登录请求使用 same-origin 且不写 localStorage", async () => {
    const api = installFetchMock();
    api.on("POST", "/api/v1/auth/login", async (request) => {
      expect(request.credentials).toBe("same-origin");
      const body = (await request.json()) as Record<string, string>;
      expect(Object.keys(body)).toEqual(["password"]);
      return jsonResponse({ authenticated: true });
    });
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const { user } = renderLogin();
    await user.type(screen.getByLabelText(/口令/), "admin-secret");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    await waitFor(() => {
      expect(screen.getByText("首页")).toBeInTheDocument();
    });
    expect(setItem).not.toHaveBeenCalled();
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});

describe("TC-010 next 只接受站内路径", () => {
  test("TC-010 登录成功后跳转到站内 next", async () => {
    const api = installFetchMock();
    api.on("POST", "/api/v1/auth/login", () =>
      jsonResponse({ authenticated: true }),
    );
    const { user } = renderLogin("/login?next=%2Fsessions");
    await user.type(screen.getByLabelText(/口令/), "admin-secret");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    expect(await screen.findByText("会话页")).toBeInTheDocument();
  });

  test("TC-010 外部 next 被拒绝并回退首页", async () => {
    const api = installFetchMock();
    api.on("POST", "/api/v1/auth/login", () =>
      jsonResponse({ authenticated: true }),
    );
    const { user } = renderLogin("/login?next=https://evil.example/phish");
    await user.type(screen.getByLabelText(/口令/), "admin-secret");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    expect(await screen.findByText("首页")).toBeInTheDocument();
    expect(screen.queryByText("会话页")).not.toBeInTheDocument();
  });
});

describe("登录页锁定 / 过期 / 登出态", () => {
  test("TC-001 锁定态展示 mm:ss 倒计时", async () => {
    const api = installFetchMock();
    api.on("POST", "/api/v1/auth/login", () =>
      jsonResponse(
        {
          code: "login_locked",
          message: "尝试次数过多，请稍后再试。",
          details: [{ retryAfterSeconds: 125 }],
          requestId: "t-lock",
        },
        429,
      ),
    );
    const { user } = renderLogin();
    await user.type(screen.getByLabelText(/口令/), "wrong");
    await user.click(screen.getByRole("button", { name: /登录/ }));
    expect(await screen.findByText(/02:05/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /登录/ })).toBeDisabled();
  });

  test("TC-001 过期态展示会话过期提示", () => {
    renderLogin("/login?reason=expired");
    expect(screen.getByText(/会话已过期，请重新登录/)).toBeInTheDocument();
  });

  test("TC-001 登出态展示已退出提示", () => {
    renderLogin("/login?reason=logged-out");
    expect(screen.getByText(/已退出登录/)).toBeInTheDocument();
  });
});
