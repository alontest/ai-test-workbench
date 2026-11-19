import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { PROMPT_MAX_CHARS } from "../composer/CharacterCounter";
import { CallPanel } from "./CallPanel";
import type { SessionSummary } from "../sessions/types";

const session: SessionSummary = {
  sessionId: 42,
  project: { projectId: 1, name: "支付中心" },
  entranceKey: "bug-analysis",
  title: "订单超时排查",
  status: "in_progress",
  model: {
    modelId: 3,
    modelName: "gpt-4.1",
    displayName: "GPT-4.1",
    providerId: 1,
    providerName: "OpenAI",
  },
  createdAt: "2026-11-18T02:00:00Z",
  updatedAt: "2026-11-18T02:00:00Z",
  closedAt: null,
};

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  const api = installFetchMock();
  return {
    user: userEvent.setup(),
    api,
    client,
    ...render(
      <QueryClientProvider client={client}>
        <CallPanel session={session} />
      </QueryClientProvider>,
    ),
  };
}

describe("TC-041 调用面板超限禁用与调用中拦截", () => {
  test("TC-041 超限禁用发起调用", () => {
    renderPanel();
    fireEvent.change(screen.getByLabelText(/提示/), {
      target: { value: "x".repeat(PROMPT_MAX_CHARS + 1) },
    });
    expect(screen.getByRole("button", { name: /发起调用/ })).toBeDisabled();
    expect(screen.getByText(/已超出上限/)).toBeInTheDocument();
  });

  test("TC-041 调用中禁用重复提交且只发一次请求", async () => {
    const { user, api } = renderPanel();
    let resolvePost: ((response: Response) => void) | undefined;
    api.on(
      "POST",
      "/api/v1/sessions/42/ai/complete",
      () =>
        new Promise<Response>((resolve) => {
          resolvePost = resolve;
        }),
    );
    await user.type(screen.getByLabelText(/提示/), "请分析日志");
    await user.click(screen.getByRole("button", { name: /发起调用/ }));
    expect(await screen.findByRole("button", { name: /调用中/ })).toBeDisabled();
    expect(api.fetch.mock.calls.length).toBe(1);
    resolvePost?.(
      jsonResponse({
        callId: 17,
        sessionId: 42,
        status: "success",
        resultText: "ok",
        latencyMs: 12,
        retryCount: 0,
        model: session.model,
        knowledgeInjection: null,
        createdAt: "2026-11-18T02:03:00Z",
        finishedAt: "2026-11-18T02:03:01Z",
      }),
    );
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /发起调用/ })).toBeEnabled();
    });
  });
});

describe("TC-025 本次参数覆盖不回写模型", () => {
  test("TC-025 提交带 temperature/maxTokens 且不 PATCH 模型", async () => {
    const { user, api } = renderPanel();
    api.on("POST", "/api/v1/sessions/42/ai/complete", async (request) => {
      const body = (await request.json()) as Record<string, unknown>;
      expect(body).toMatchObject({
        prompt: "请分析日志",
        temperature: 0.2,
        maxTokens: 2048,
      });
      expect(body).not.toHaveProperty("knowledgeRefs");
      return jsonResponse({
        callId: 17,
        sessionId: 42,
        status: "success",
        resultText: "ok",
        latencyMs: 12,
        retryCount: 0,
        model: session.model,
        knowledgeInjection: null,
      });
    });
    await user.click(screen.getByRole("button", { name: /高级参数/ }));
    await user.clear(screen.getByLabelText(/temperature/i));
    await user.type(screen.getByLabelText(/temperature/i), "0.2");
    await user.clear(screen.getByLabelText(/max_tokens|maxTokens/i));
    await user.type(screen.getByLabelText(/max_tokens|maxTokens/i), "2048");
    await user.type(screen.getByLabelText(/提示/), "请分析日志");
    await user.click(screen.getByRole("button", { name: /发起调用/ }));
    await waitFor(() => {
      expect(api.fetch).toHaveBeenCalled();
    });
    const patched = api.fetch.mock.calls.filter(([, init]) => {
      const method = init?.method?.toUpperCase();
      return method === "PATCH" || method === "PUT";
    });
    expect(patched).toHaveLength(0);
  });
});

describe("TC-044 失败保留面板内容并展示错误码", () => {
  test("TC-044 调用失败后提示仍在且展示错误码", async () => {
    const { user, api } = renderPanel();
    api.on("POST", "/api/v1/sessions/42/ai/complete", () =>
      jsonResponse(
        {
          code: "ai_auth",
          message: "上游鉴权失败。",
          details: [{ callId: 18, retryCount: 1, message: "上游鉴权失败。" }],
          requestId: "t-auth",
        },
        502,
      ),
    );
    await user.type(screen.getByLabelText(/提示/), "请分析日志");
    await user.click(screen.getByRole("button", { name: /发起调用/ }));
    expect(await screen.findByText(/ai_auth/)).toBeInTheDocument();
    expect(screen.getByLabelText(/提示/)).toHaveValue("请分析日志");
    expect(screen.queryByText(/sk-/)).not.toBeInTheDocument();
  });
});
