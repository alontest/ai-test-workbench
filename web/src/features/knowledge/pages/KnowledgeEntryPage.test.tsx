import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { KnowledgeEntryPage } from "./KnowledgeEntryPage";

const item = {
  entryId: "e1",
  code: "BR-003",
  title: "重复支付拦截",
  type: "rule",
  kbId: "kb1",
  kbName: "支付域知识库",
  kbVersion: 2,
  superseded: false,
  bodyMissing: true,
  freshness: { at: null, state: "unknown" },
  conflict: { hasConflict: false },
};

const detail = {
  entryId: "e1",
  code: "BR-003",
  title: "重复支付拦截",
  type: "rule",
  kb: {
    kbId: "kb1",
    name: "支付域知识库",
    version: 2,
    generatedAt: null,
    current: true,
    superseded: false,
    latestKbId: "kb1",
  },
  summary: "摘要文本",
  body: null,
  bodyMissing: true,
  bodySourceFile: null,
  sourceDoc: null,
  anchor: null,
  fields: {},
  tables: [],
  codePaths: [],
  neighbors: [],
  freshness: { at: null, state: "unknown" },
  conflicts: [],
  createdAt: "2026-11-18T02:30:00Z",
};

function renderPage() {
  return renderWithApp(<KnowledgeEntryPage />, {
    route: "/knowledge-bases/kb1/entries/BR-003",
    routes: (
      <Routes>
        <Route
          path="/knowledge-bases/:kbId/entries/:code"
          element={<KnowledgeEntryPage />}
        />
      </Routes>
    ),
  });
}

describe("KB-017 条目详情降级", () => {
  test("正文缺失时展示摘要并标注，字段缺失显示破折号", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/knowledge-bases/kb1/entries", () =>
      jsonResponse({
        items: [item],
        countsByType: {
          term: 0,
          entity: 0,
          state: 0,
          rule: 1,
          process: 0,
          api: 0,
          domain_event: 0,
          other: 0,
        },
        total: 1,
        nextCursor: null,
      }),
    );
    api.on("GET", "/api/v1/knowledge-entries/e1", () => jsonResponse(detail));
    renderPage();
    expect((await screen.findAllByText("摘要文本")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("正文缺失").length).toBeGreaterThan(0);
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.queryByText(/<script/i)).not.toBeInTheDocument();
  });

  test("编号不存在时展示空态而不是错误", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/knowledge-bases/kb1/entries", () =>
      jsonResponse({
        items: [],
        countsByType: {},
        total: 0,
        nextCursor: null,
      }),
    );
    renderPage();
    expect(await screen.findByText("条目不存在")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
