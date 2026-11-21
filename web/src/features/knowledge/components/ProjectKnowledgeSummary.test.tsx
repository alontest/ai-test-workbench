import { screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { ProjectKnowledgeSummary } from "./ProjectKnowledgeSummary";

function kb(index: number) {
  const kbId = String(index).repeat(32);
  return {
    kbId,
    projectId: 1,
    name: `知识库 ${index}`,
    version: 1,
    current: true,
    status: "ready",
    generatedAt: null,
    entryCount: index,
    fileCount: 1,
    totalByteSize: 10,
    supersededCount: 0,
    latestKbId: kbId,
    createdAt: "2026-11-18T02:30:00Z",
    project: { id: 1, name: "支付台" },
  };
}

describe("KB-018 项目知识库摘要", () => {
  test("展示最多 3 个并提示剩余数量", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/knowledge-bases", () =>
      jsonResponse({
        items: [kb(1), kb(2), kb(3), kb(4), kb(5)],
        nextCursor: null,
      }),
    );
    renderWithApp(<ProjectKnowledgeSummary />);
    expect(await screen.findByText("知识库 1")).toBeInTheDocument();
    expect(screen.getByText("知识库 3")).toBeInTheDocument();
    expect(screen.queryByText("知识库 4")).not.toBeInTheDocument();
    expect(
      screen.getByText(/还有 2 个（最多展示 3 个）/),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/生成于\s*未知/).length).toBeGreaterThan(0);
  });

  test("没有知识库时展示 0 态", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/knowledge-bases", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    renderWithApp(<ProjectKnowledgeSummary />);
    expect(await screen.findByText(/还没有关联知识库/)).toBeInTheDocument();
  });
});
