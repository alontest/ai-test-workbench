import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../../test/fetch";
import { renderWithApp } from "../../../test/render";
import { KnowledgeImportPage } from "./KnowledgeImportPage";

function mockProjects(api: ReturnType<typeof installFetchMock>) {
  api.on("GET", "/api/v1/projects", () =>
    jsonResponse({
      items: [{ projectId: 1, name: "支付台" }],
      nextCursor: null,
    }),
  );
}

function renderPage() {
  return {
    user: userEvent.setup(),
    ...renderWithApp(<KnowledgeImportPage />),
  };
}

async function selectProject(user: ReturnType<typeof userEvent.setup>) {
  await screen.findByRole("option", { name: "支付台" });
  await user.selectOptions(screen.getByLabelText("项目"), "1");
}

describe("KB-016 导入页即时校验", () => {
  test("拒绝不支持的扩展名并禁用提交", async () => {
    const api = installFetchMock();
    mockProjects(api);
    const user = userEvent.setup({ applyAccept: false });
    renderWithApp(<KnowledgeImportPage />);
    await selectProject(user);
    await user.upload(
      screen.getByLabelText("选择知识库文件"),
      new File(["x"], "notes.txt", { type: "text/plain" }),
    );
    expect(await screen.findByText(/不支持 \.txt/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交导入" })).toBeDisabled();
  });

  test("缺少 index.json 时禁用提交", async () => {
    const api = installFetchMock();
    mockProjects(api);
    const { user } = renderPage();
    await selectProject(user);
    await user.upload(
      screen.getByLabelText("选择知识库文件"),
      new File(["# a"], "a.md", { type: "text/markdown" }),
    );
    expect(await screen.findByText("必须包含 index.json")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交导入" })).toBeDisabled();
  });

  test("超过 50 个文件时禁用提交", async () => {
    const api = installFetchMock();
    mockProjects(api);
    const { user } = renderPage();
    await selectProject(user);
    const files = [
      new File(["{}"], "index.json", { type: "application/json" }),
      ...Array.from(
        { length: 50 },
        (_item, index) => new File(["x"], `f${index}.md`, { type: "text/markdown" }),
      ),
    ];
    await user.upload(screen.getByLabelText("选择知识库文件"), files);
    expect(await screen.findByText(/单次最多 50 个文件/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "提交导入" })).toBeDisabled();
  });

  test("提交成功后展示导入报告与版本提示", async () => {
    const api = installFetchMock();
    mockProjects(api);
    api.on("POST", "/api/v1/knowledge-bases", () =>
      jsonResponse(
        {
          kb: {
            kbId: "a".repeat(32),
            projectId: 1,
            name: "支付域知识库",
            version: 2,
            current: true,
            status: "ready",
            generatedAt: null,
            entryCount: 184,
            fileCount: 2,
            totalByteSize: 100,
            supersededCount: 1,
            latestKbId: "a".repeat(32),
            createdAt: "2026-11-18T02:30:00Z",
          },
          importReport: {
            files: [],
            skippedEntries: [
              { index: 17, line: 214, code: "ENT-bad", reason: "invalid_id" },
            ],
            unmatchedFiles: ["notes.md"],
            duplicateBodies: [],
            counts: { files: 2, bytes: 100, entries: 184, skipped: 1 },
            versionBumped: true,
            previousVersion: 1,
          },
        },
        201,
      ),
    );
    const { user } = renderPage();
    await selectProject(user);
    await user.upload(screen.getByLabelText("选择知识库文件"), [
      new File(["{}"], "index.json", { type: "application/json" }),
      new File(["# a"], "a.md", { type: "text/markdown" }),
    ]);
    await user.click(await screen.findByRole("button", { name: "提交导入" }));
    expect(await screen.findByText(/已导入 184 条/)).toBeInTheDocument();
    expect(screen.getByText(/第 214 行/)).toBeInTheDocument();
    expect(screen.getByText(/invalid_id/)).toBeInTheDocument();
    expect(screen.getByText(/同名重新导入，已生成新版本/)).toBeInTheDocument();
    expect(screen.queryByText(/SENTINEL/)).not.toBeInTheDocument();
  });
});
