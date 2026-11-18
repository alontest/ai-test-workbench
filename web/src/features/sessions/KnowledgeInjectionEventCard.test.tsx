import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { CallRecordRow } from "../calls/CallRecordRow";
import type { CallRecord } from "../calls/types";
import { KnowledgeInjectionEventCard } from "./KnowledgeInjectionEventCard";
import { TimelineEvent } from "./TimelineEvent";
import type { SessionEvent } from "./types";

const payload = {
  items: [
    {
      kbId: 5,
      kbName: "支付中心知识库",
      kbVersion: 2,
      entryCodes: ["ENT-012", "BR-003"],
      injectedChars: 1840,
      kbDeleted: true,
    },
  ],
  promptChars: 12,
  injectedChars: 1840,
  totalChars: 1852,
  excludedCodes: ["ENT-009"],
};

describe("TC-070 知识库注入事件卡片", () => {
  test("TC-070 渲染知识库名版本编号字数与已删除标记", () => {
    render(<KnowledgeInjectionEventCard payload={payload} />);
    expect(screen.getByText(/支付中心知识库/)).toBeInTheDocument();
    expect(screen.getByText(/v2/)).toBeInTheDocument();
    expect(screen.getByText(/ENT-012/)).toBeInTheDocument();
    expect(screen.getByText(/BR-003/)).toBeInTheDocument();
    expect(screen.getAllByText(/1,840/).length).toBeGreaterThan(0);
    expect(screen.getByText(/ENT-009/)).toBeInTheDocument();
    expect(screen.getByText(/知识库已删除/)).toBeInTheDocument();
    expect(screen.queryByText(/注入正文/)).not.toBeInTheDocument();
    expect(screen.queryByText(/body/i)).not.toBeInTheDocument();
  });

  test("TC-070 无注入不渲染", () => {
    const { container } = render(
      <KnowledgeInjectionEventCard
        payload={{
          items: [],
          promptChars: 12,
          injectedChars: 0,
          totalChars: 12,
          excludedCodes: [],
        }}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  test("TC-070 时间线按类型渲染注入卡片", () => {
    const event: SessionEvent = {
      eventId: 9,
      sessionId: 42,
      type: "knowledge_injection",
      payload,
      createdAt: "2026-11-18T02:03:00Z",
    };
    render(<TimelineEvent event={event} />);
    expect(screen.getByText(/支付中心知识库/)).toBeInTheDocument();
    expect(screen.getByText(/知识库已删除/)).toBeInTheDocument();
  });
});

describe("TC-070 调用记录行展示注入快照", () => {
  test("TC-070 展开后标知识库已删除且无注入不渲染", async () => {
    const call: CallRecord = {
      callId: 17,
      sessionId: 42,
      project: { projectId: 1, name: "支付中心" },
      model: { modelId: 3, displayName: "GPT-4.1", providerName: "OpenAI" },
      status: "success",
      promptPreview: "请分析",
      promptCharCount: 3,
      knowledgeInjection: [
        {
          kbId: 5,
          kbName: "支付中心知识库",
          kbVersion: 2,
          entryCodes: ["ENT-012"],
          injectedChars: 1840,
          kbDeleted: true,
        },
      ],
      latencyMs: 12,
      retryCount: 0,
      errorCode: null,
      errorMessage: null,
      createdAt: "2026-11-18T02:03:00Z",
      finishedAt: "2026-11-18T02:03:01Z",
    };
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false, gcTime: 0 } },
    });
    const api = installFetchMock();
    api.on("GET", "/api/v1/calls/17", () =>
      jsonResponse({ ...call, resultText: "ok" }),
    );
    render(
      <QueryClientProvider client={client}>
        <table>
          <tbody>
            <CallRecordRow call={call} />
          </tbody>
        </table>
      </QueryClientProvider>,
    );
    fireEvent.click(screen.getByRole("button", { name: /展开核对/ }));
    expect(await screen.findByText(/支付中心知识库/)).toBeInTheDocument();
    expect(screen.getByText(/知识库已删除/)).toBeInTheDocument();
  });
});
