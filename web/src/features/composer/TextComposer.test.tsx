import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { PROMPT_MAX_CHARS } from "./CharacterCounter";
import { TextComposer } from "./TextComposer";

function renderComposer() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  const api = installFetchMock();
  const invalidate = vi.spyOn(client, "invalidateQueries");
  return {
    user: userEvent.setup(),
    api,
    invalidate,
    ...render(
      <QueryClientProvider client={client}>
        <TextComposer sessionId={42} />
      </QueryClientProvider>,
    ),
  };
}

describe("TC-033 空或纯空白正文拒绝", () => {
  test("TC-033 空正文就地错误且不发起请求", async () => {
    const { user, api } = renderComposer();
    await user.type(screen.getByLabelText(/标题/), "报错日志");
    await user.click(screen.getByRole("button", { name: /添加到时间线/ }));
    expect(screen.getByRole("alert")).toHaveTextContent(/正文必填/);
    expect(api.fetch).not.toHaveBeenCalled();
  });
});

describe("TC-034 字数计数分档与超限禁用", () => {
  test("TC-034 >90% 警告色、超限危险色且禁用提交", () => {
    renderComposer();
    const body = screen.getByLabelText(/正文/);
    fireEvent.change(body, {
      target: { value: "x".repeat(Math.floor(PROMPT_MAX_CHARS * 0.9) + 1) },
    });
    expect(screen.getByRole("status", { name: /字数/ })).toHaveAttribute(
      "data-state",
      "warning",
    );

    fireEvent.change(body, {
      target: { value: "x".repeat(PROMPT_MAX_CHARS + 1) },
    });
    expect(screen.getByRole("status", { name: /字数/ })).toHaveAttribute(
      "data-state",
      "exceeded",
    );
    expect(screen.getByText(/已超出上限/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /添加到时间线/ })).toBeDisabled();
  });
});

describe("TC-032 提交文本追加 input_text 事件", () => {
  test("TC-032 成功提交后清空并请求 inputs/text", async () => {
    const { user, api, invalidate } = renderComposer();
    api.on("POST", "/api/v1/sessions/42/inputs/text", async (request) => {
      const body = (await request.json()) as { title: string; text: string };
      expect(body).toEqual({ title: "报错日志", text: "boom trace" });
      return jsonResponse(
        {
          eventId: 7,
          sessionId: 42,
          type: "input_text",
          payload: { title: "报错日志", text: "boom trace", charCount: 10 },
          createdAt: "2026-11-18T02:01:00Z",
        },
        201,
      );
    });
    await user.type(screen.getByLabelText(/标题/), "报错日志");
    await user.type(screen.getByLabelText(/正文/), "boom trace");
    await user.click(screen.getByRole("button", { name: /添加到时间线/ }));
    await waitFor(() => {
      expect(screen.getByLabelText(/正文/)).toHaveValue("");
    });
    expect(invalidate).toHaveBeenCalled();
  });
});
