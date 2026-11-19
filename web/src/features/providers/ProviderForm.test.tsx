import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { ConnectionTestBadge, type ConnectionTestState } from "./ConnectionTestBadge";
import { ProvidersPage } from "./ProvidersPage";
import { SecretField } from "./SecretField";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ProvidersPage />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-017 密钥掩码且不回显原文", () => {
  test("TC-017 列表与编辑展示掩码不含明文密钥", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/providers", () =>
      jsonResponse({
        items: [
          {
            providerId: 1,
            name: "OpenAI",
            protocol: "openai_compatible",
            baseUrl: "https://api.openai.com/v1",
            apiKeyMasked: "sk-****abcd",
            enabled: true,
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    const { user } = renderPage();
    expect(await screen.findByText("sk-****abcd")).toBeInTheDocument();
    expect(screen.queryByText(/sk-e77|sk-live/)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /编辑/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(/密钥/)).toHaveValue("");
    expect(
      within(dialog).getByPlaceholderText("sk-****abcd"),
    ).toBeInTheDocument();
  });

  test("TC-017 编辑留空提交不带 apiKey", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/providers", () =>
      jsonResponse({
        items: [
          {
            providerId: 1,
            name: "OpenAI",
            protocol: "openai_compatible",
            baseUrl: "https://api.openai.com/v1",
            apiKeyMasked: "sk-****abcd",
            enabled: true,
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    let patchBody: Record<string, unknown> | undefined;
    api.on("PATCH", "/api/v1/providers/1", async (request) => {
      patchBody = (await request.json()) as Record<string, unknown>;
      return jsonResponse({
        providerId: 1,
        name: "OpenAI 2",
        protocol: "openai_compatible",
        baseUrl: "https://api.openai.com/v1",
        apiKeyMasked: "sk-****abcd",
        enabled: true,
        createdAt: "2026-11-18T02:00:00Z",
        updatedAt: "2026-11-18T03:00:00Z",
      });
    });
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /编辑/ }));
    const dialog = await screen.findByRole("dialog");
    const name = within(dialog).getByLabelText(/名称/);
    await user.clear(name);
    await user.type(name, "OpenAI 2");
    await user.click(within(dialog).getByRole("button", { name: /保存/ }));
    await waitFor(() => {
      expect(patchBody).toBeDefined();
    });
    expect(patchBody).not.toHaveProperty("apiKey");
  });
});

describe("TC-018 提供商字段校验", () => {
  test("TC-018 非法 baseUrl 错误落在字段上", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/providers", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("POST", "/api/v1/providers", () =>
      jsonResponse(
        {
          code: "validation_error",
          message: "请求参数校验失败。",
          details: [{ field: "baseUrl", message: "必须是 http(s) 绝对地址" }],
          requestId: "t-url",
        },
        400,
      ),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建提供商|新建/ }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/名称/), "Bad");
    await user.selectOptions(
      within(dialog).getByLabelText(/协议/),
      "openai_compatible",
    );
    await user.type(
      within(dialog).getByLabelText(/Base URL|地址/i),
      "not-a-url",
    );
    await user.type(within(dialog).getByLabelText(/密钥/), "sk-test");
    await user.click(within(dialog).getByRole("button", { name: /保存|创建/ }));
    expect(await screen.findByText(/http\(s\) 绝对地址/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(/Base URL|地址/i)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});

describe("TC-021 ConnectionTestBadge 七态", () => {
  test("TC-021 七态均可渲染", () => {
    const cases: Array<{
      state: ConnectionTestState;
      result?: { ok: boolean; latencyMs: number; errorCode?: string };
      text: RegExp;
    }> = [
      { state: "idle", text: /测试连接/ },
      { state: "testing", text: /测试中/ },
      {
        state: "success",
        result: { ok: true, latencyMs: 420 },
        text: /成功|可达/,
      },
      {
        state: "auth-error",
        result: { ok: false, latencyMs: 80, errorCode: "auth" },
        text: /鉴权|认证/,
      },
      {
        state: "unreachable",
        result: { ok: false, latencyMs: 10, errorCode: "unreachable" },
        text: /不可达|网络/,
      },
      {
        state: "timeout",
        result: { ok: false, latencyMs: 10000, errorCode: "timeout" },
        text: /超时/,
      },
      {
        state: "credential-unavailable",
        result: { ok: false, latencyMs: 0, errorCode: "credential_unavailable" },
        text: /凭据不可用|无法解密/,
      },
    ];
    const { rerender } = render(
      <ConnectionTestBadge state="idle" onTest={() => undefined} />,
    );
    for (const item of cases) {
      rerender(
        <ConnectionTestBadge
          state={item.state}
          result={item.result}
          onTest={() => undefined}
        />,
      );
      expect(screen.getByText(item.text)).toBeInTheDocument();
    }
    rerender(
      <ConnectionTestBadge state="testing" onTest={() => undefined} />,
    );
    expect(screen.getByRole("button", { name: /测试连接/ })).toBeDisabled();
  });

  test("TC-021 表单变更后测试结果回到 idle", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/providers", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("POST", "/api/v1/providers/connection-test", () =>
      jsonResponse({ ok: true, latencyMs: 200, modelCount: 3, errorCode: null }),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建提供商|新建/ }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/名称/), "OpenAI");
    await user.selectOptions(
      within(dialog).getByLabelText(/协议/),
      "openai_compatible",
    );
    await user.type(
      within(dialog).getByLabelText(/Base URL|地址/i),
      "https://api.openai.com/v1",
    );
    await user.type(within(dialog).getByLabelText(/密钥/), "sk-test");
    await user.click(within(dialog).getByRole("button", { name: /测试连接/ }));
    expect(await within(dialog).findByText(/成功|可达/)).toBeInTheDocument();
    await user.type(within(dialog).getByLabelText(/密钥/), "x");
    expect(within(dialog).queryByText(/成功|可达/)).not.toBeInTheDocument();
  });
});

describe("SecretField", () => {
  test("TC-017 掩码占位且输入为口令类型", () => {
    function Harness() {
      const [value, setValue] = useState("");
      return (
        <SecretField
          maskedValue="sk-****abcd"
          value={value}
          onChange={setValue}
        />
      );
    }
    render(<Harness />);
    const input = screen.getByLabelText(/密钥/);
    expect(input).toHaveAttribute("type", "password");
    expect(input).toHaveAttribute("placeholder", "sk-****abcd");
  });
});
