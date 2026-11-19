import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import {
  installFetchMock,
  jsonResponse,
  type MockHandler,
} from "../../test/fetch";
import { ModelsPage } from "./ModelsPage";

function renderPage(
  extra: Array<[string, string, MockHandler]> = [],
) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const api = installFetchMock();
  api.on("GET", "/api/v1/providers/1", () =>
    jsonResponse({
      providerId: 1,
      name: "OpenAI",
      protocol: "openai_compatible",
      baseUrl: "https://api.openai.com/v1",
      apiKeyMasked: "sk-****abcd",
      enabled: true,
      createdAt: "2026-11-18T02:00:00Z",
      updatedAt: "2026-11-18T02:00:00Z",
    }),
  );
  for (const [method, path, impl] of extra) {
    api.on(method, path, impl);
  }
  return {
    user: userEvent.setup(),
    api,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/providers/1/models"]}>
          <Routes>
            <Route path="/providers/:id/models" element={<ModelsPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-023 模型参数范围", () => {
  test("TC-023 temperature 越界提示落在字段上", async () => {
    const { user } = renderPage([
      [
        "GET",
        "/api/v1/providers/1/models",
        () => jsonResponse({ items: [], nextCursor: null }),
      ],
      [
        "POST",
        "/api/v1/providers/1/models",
        () =>
          jsonResponse(
            {
              code: "validation_error",
              message: "请求参数校验失败。",
              details: [
                {
                  field: "defaultTemperature",
                  message: "temperature 必须在 0–2 之间",
                },
              ],
              requestId: "t-temp",
            },
            400,
          ),
      ],
    ]);
    await user.click(await screen.findByRole("button", { name: /新建模型|新增/ }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/模型名/), "gpt-4.1");
    await user.type(within(dialog).getByLabelText(/显示名/), "GPT-4.1");
    const temperature = within(dialog).getByLabelText(/temperature/i);
    await user.clear(temperature);
    await user.type(temperature, "2.01");
    await user.click(within(dialog).getByRole("button", { name: /保存|创建/ }));
    expect(await screen.findByText(/0–2|0-2/)).toBeInTheDocument();
    expect(temperature).toHaveAttribute("aria-invalid", "true");
  });
});

describe("TC-024 同提供商重名", () => {
  test("TC-024 重名提示 model_name_duplicate 并定位模型名", async () => {
    const { user } = renderPage([
      [
        "GET",
        "/api/v1/providers/1/models",
        () =>
          jsonResponse({
            items: [
              {
                modelId: 3,
                providerId: 1,
                modelName: "gpt-4.1",
                displayName: "GPT-4.1",
                defaultTemperature: 0.7,
                defaultMaxTokens: 4096,
                enabled: true,
                createdAt: "2026-11-18T02:00:00Z",
              },
            ],
            nextCursor: null,
          }),
      ],
      [
        "POST",
        "/api/v1/providers/1/models",
        () =>
          jsonResponse(
            {
              code: "model_name_duplicate",
              message: "同一提供商下模型名称已存在。",
              details: [
                { field: "modelName", message: "同一提供商下模型名称已存在" },
              ],
              requestId: "t-dup",
            },
            409,
          ),
      ],
    ]);
    await user.click(await screen.findByRole("button", { name: /新建模型|新增/ }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/模型名/), "gpt-4.1");
    await user.type(within(dialog).getByLabelText(/显示名/), "GPT-4.1 副本");
    await user.click(within(dialog).getByRole("button", { name: /保存|创建/ }));
    expect(
      await screen.findByText(/同一提供商下模型名称已存在/),
    ).toBeInTheDocument();
    expect(within(dialog).getByLabelText(/模型名/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});

describe("停用后从可选列表消失", () => {
  test("TC-023 停用开关可提交 enabled=false", async () => {
    let patchBody: Record<string, unknown> | undefined;
    const { user } = renderPage([
      [
        "GET",
        "/api/v1/providers/1/models",
        () =>
          jsonResponse({
            items: [
              {
                modelId: 3,
                providerId: 1,
                modelName: "gpt-4.1",
                displayName: "GPT-4.1",
                defaultTemperature: 0.7,
                defaultMaxTokens: 4096,
                enabled: true,
                createdAt: "2026-11-18T02:00:00Z",
              },
            ],
            nextCursor: null,
          }),
      ],
      [
        "PATCH",
        "/api/v1/models/3",
        async (request) => {
          patchBody = (await request.json()) as Record<string, unknown>;
          return jsonResponse({
            modelId: 3,
            providerId: 1,
            modelName: "gpt-4.1",
            displayName: "GPT-4.1",
            defaultTemperature: 0.7,
            defaultMaxTokens: 4096,
            enabled: false,
            createdAt: "2026-11-18T02:00:00Z",
          });
        },
      ],
    ]);
    await waitFor(() => {
      expect(screen.getByText("gpt-4.1")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("switch"));
    await waitFor(() => {
      expect(patchBody).toEqual({ enabled: false });
    });
  });
});
