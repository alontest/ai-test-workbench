import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { renderWithApp } from "../../test/render";
import { CallPanel } from "../calls/CallPanel";
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

const candidate = {
  entryId: "e1",
  code: "ENT-001",
  title: "支付单",
  type: "entity",
  kbId: "kb1",
  kbName: "支付域知识库",
  kbVersion: 2,
  superseded: false,
  bodyMissing: false,
  freshness: { at: null, state: "unknown" },
  conflict: { hasConflict: false },
};

const countsByType = {
  term: 0,
  entity: 1,
  state: 0,
  rule: 0,
  process: 0,
  api: 0,
  domain_event: 0,
  other: 0,
};

function mockCandidates(api: ReturnType<typeof installFetchMock>) {
  api.on(
    "GET",
    "/api/v1/sessions/42/knowledge-injection/candidates",
    () =>
      jsonResponse({
        projectId: 1,
        items: [candidate],
        countsByType,
        total: 1,
        nextCursor: null,
      }),
  );
}

function mockPreview(
  api: ReturnType<typeof installFetchMock>,
  overLimit: boolean,
) {
  api.on(
    "POST",
    "/api/v1/sessions/42/knowledge-injection/preview",
    async (request) => {
      const body = (await request.json()) as { refs: { kbId: string; code: string }[] };
      const injected = overLimit ? 250_000 : 120;
      return jsonResponse({
        items: body.refs.map((ref) => ({
          kbId: ref.kbId,
          kbName: "支付域知识库",
          kbVersion: 2,
          code: ref.code,
          title: "支付单",
          chars: injected,
          source: "body",
        })),
        invalidItems: [],
        promptChars: 4,
        injectedChars: injected,
        totalChars: injected + 4,
        limit: 200_000,
        overLimit,
        warnings: [],
      });
    },
  );
}

function renderPanel() {
  return {
    user: userEvent.setup(),
    ...renderWithApp(<CallPanel session={session} />),
  };
}

async function selectEntry(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    await screen.findByRole("checkbox", { name: "选择 ENT-001" }),
  );
}

function invalidEntriesResponse() {
  return jsonResponse(
    {
      code: "knowledge_invalid_entries",
      message: "部分知识库条目已失效，确认后才能继续。",
      details: {
        invalidItems: [
          { kbId: "kb1", code: "ENT-001", reason: "superseded" },
        ],
      },
      requestId: "req-invalid",
    },
    409,
  );
}

describe("KB-018 会话知识注入", () => {
  test("超预算时阻塞发起调用并注明不会截断", async () => {
    const api = installFetchMock();
    mockCandidates(api);
    mockPreview(api, true);
    const { user } = renderPanel();
    await user.type(screen.getByLabelText(/提示/), "请分析");
    await selectEntry(user);
    expect(
      await screen.findByText(/不会截断/, undefined, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/已选 1 条/).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /发起调用/ })).toBeDisabled();
  });

  test("409 失效项需确认，确认后带 confirmInvalidCodes 重试", async () => {
    const api = installFetchMock();
    mockCandidates(api);
    mockPreview(api, false);
    const bodies: Record<string, unknown>[] = [];
    api.on(
      "POST",
      "/api/v1/sessions/42/ai/complete",
      async (request) => {
        const body = (await request.json()) as Record<string, unknown>;
        bodies.push(body);
        if (bodies.length === 1) {
          return invalidEntriesResponse();
        }
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
      },
    );
    const { user } = renderPanel();
    await user.type(screen.getByLabelText(/提示/), "请分析");
    await selectEntry(user);
    await user.click(screen.getByRole("button", { name: /发起调用/ }));
    const dialog = await screen.findByRole("alertdialog");
    expect(dialog).toHaveTextContent("已被新版本取代");
    expect(within(dialog).getByText(/不会发起调用/)).toBeInTheDocument();
    await user.click(within(dialog).getByRole("button", { name: "继续调用" }));
    await waitFor(() => expect(bodies).toHaveLength(2));
    expect(bodies[0].knowledgeRefs).toEqual([
      { kbId: "kb1", entryCodes: ["ENT-001"] },
    ]);
    expect(bodies[0]).not.toHaveProperty("confirmInvalidCodes");
    expect(bodies[1].confirmInvalidCodes).toEqual([
      { kbId: "kb1", code: "ENT-001" },
    ]);
    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    });
  });

  test("取消失效确认后不再发起调用", async () => {
    const api = installFetchMock();
    mockCandidates(api);
    mockPreview(api, false);
    let calls = 0;
    api.on("POST", "/api/v1/sessions/42/ai/complete", () => {
      calls += 1;
      return invalidEntriesResponse();
    });
    const { user } = renderPanel();
    await user.type(screen.getByLabelText(/提示/), "请分析");
    await selectEntry(user);
    await user.click(screen.getByRole("button", { name: /发起调用/ }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "取消" }));
    await waitFor(() => {
      expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    });
    expect(calls).toBe(1);
  });
});
