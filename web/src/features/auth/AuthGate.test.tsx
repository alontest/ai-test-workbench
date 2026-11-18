import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { describe, expect, test } from "vitest";
import { AuthGate } from "../../app/AuthGate";
import { installFetchMock, jsonResponse } from "../../test/fetch";

function LoginProbe() {
  const location = useLocation();
  return (
    <div>
      登录页
      <span data-testid="search">{location.search}</span>
    </div>
  );
}

function renderGate(route: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/login" element={<LoginProbe />} />
          <Route element={<AuthGate />}>
            <Route path="/sessions" element={<div>会话页</div>} />
            <Route path="/projects" element={<div>项目页</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TC-001 AuthGate 未认证跳转", () => {
  test("TC-001 未登录访问业务页跳转到登录并保留站内 next", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/auth/session", () =>
      jsonResponse(
        {
          code: "unauthorized",
          message: "未登录或会话已过期。",
          details: [],
          requestId: "t-1",
        },
        401,
      ),
    );
    renderGate("/sessions");
    expect(await screen.findByText("登录页")).toBeInTheDocument();
    expect(screen.queryByText("会话页")).not.toBeInTheDocument();
    expect(screen.getByTestId("search").textContent).toContain("next=");
    expect(
      decodeURIComponent(screen.getByTestId("search").textContent ?? ""),
    ).toContain("/sessions");
  });

  test("TC-010 AuthGate 的 next 只接受站内路径", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/auth/session", () =>
      jsonResponse(
        {
          code: "unauthorized",
          message: "未登录或会话已过期。",
          details: [],
          requestId: "t-2",
        },
        401,
      ),
    );
    renderGate("/projects");
    expect(await screen.findByText("登录页")).toBeInTheDocument();
    const search = screen.getByTestId("search").textContent ?? "";
    expect(search).not.toMatch(/https?:/);
    expect(search).not.toContain("//example.com");
    expect(decodeURIComponent(search)).toContain("/projects");
  });

  test("TC-001 已认证时渲染子路由", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/auth/session", () =>
      jsonResponse({
        authenticated: true,
        lastSeenAt: "2026-11-18T02:00:00Z",
        idleExpiresAt: "2026-11-18T10:00:00Z",
      }),
    );
    renderGate("/sessions");
    expect(await screen.findByText("会话页")).toBeInTheDocument();
    expect(screen.queryByText("登录页")).not.toBeInTheDocument();
  });

  test("TC-001 AuthGate 校验中展示检查态", async () => {
    const api = installFetchMock();
    api.on(
      "GET",
      "/api/v1/auth/session",
      () =>
        new Promise((resolve) => {
          setTimeout(
            () =>
              resolve(
                jsonResponse({
                  authenticated: true,
                  lastSeenAt: "2026-11-18T02:00:00Z",
                  idleExpiresAt: "2026-11-18T10:00:00Z",
                }),
              ),
            50,
          );
        }),
    );
    renderGate("/sessions");
    expect(screen.getByText(/正在校验登录状态/)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("会话页")).toBeInTheDocument();
    });
  });
});
