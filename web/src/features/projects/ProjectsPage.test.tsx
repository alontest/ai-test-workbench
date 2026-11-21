import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { installFetchMock, jsonResponse } from "../../test/fetch";
import { ProjectsPage } from "./ProjectsPage";

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return {
    user: userEvent.setup(),
    client,
    ...render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <ProjectsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    ),
  };
}

describe("TC-013 项目创建与重名", () => {
  test("TC-013 空态展示引导且无删除按钮", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    renderPage();
    expect(await screen.findByText(/还没有项目|暂无项目/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /删除/ })).not.toBeInTheDocument();
  });

  test("TC-013 重名错误定位到名称字段", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({
        items: [
          {
            projectId: 1,
            name: "支付中心",
            repoUrl: "https://git.example.com/pay",
            techStack: "Java 21",
            requirementSource: "PRD",
            notes: "",
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T02:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    api.on("POST", "/api/v1/projects", () =>
      jsonResponse(
        {
          code: "project_name_duplicate",
          message: "项目名称已存在。",
          details: [{ field: "name", message: "项目名称已存在" }],
          requestId: "t-dup",
        },
        409,
      ),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建项目/ }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/项目名称|名称/), "支付中心");
    await user.click(within(dialog).getByRole("button", { name: /保存|创建/ }));
    expect(await screen.findByText("项目名称已存在")).toBeInTheDocument();
    const nameField = within(dialog).getByLabelText(/项目名称|名称/);
    expect(nameField).toHaveAttribute("aria-invalid", "true");
  });
});

describe("TC-014 编辑回显", () => {
  test("TC-014 编辑对话框回显项目字段", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({
        items: [
          {
            projectId: 1,
            name: "支付中心",
            repoUrl: "https://git.example.com/pay",
            techStack: "Java 21 / MySQL",
            requirementSource: "PRD v3",
            notes: "备注",
            createdAt: "2026-11-18T02:00:00Z",
            updatedAt: "2026-11-18T03:00:00Z",
          },
        ],
        nextCursor: null,
      }),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /编辑/ }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByLabelText(/项目名称|名称/)).toHaveValue("支付中心");
    expect(within(dialog).getByLabelText(/仓库/)).toHaveValue(
      "https://git.example.com/pay",
    );
    expect(within(dialog).getByLabelText(/技术栈/)).toHaveValue("Java 21 / MySQL");
  });
});

describe("TC-016 名称校验逐字段", () => {
  test("TC-016 名称为空时错误落在名称字段", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("POST", "/api/v1/projects", () =>
      jsonResponse(
        {
          code: "validation_error",
          message: "请求参数校验失败。",
          details: [{ field: "name", message: "名称不能为空" }],
          requestId: "t-empty",
        },
        400,
      ),
    );
    const { user } = renderPage();
    await user.click(await screen.findByRole("button", { name: /新建项目/ }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /保存|创建/ }));
    expect(await screen.findByText(/名称不能为空|不能为空/)).toBeInTheDocument();
    expect(within(dialog).getByLabelText(/项目名称|名称/)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });
});

describe("知识库挂载位", () => {
  test("ProjectKnowledgeSummary 保留挂载位并展示 0 个知识库", async () => {
    const api = installFetchMock();
    api.on("GET", "/api/v1/projects", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    api.on("GET", "/api/v1/knowledge-bases", () =>
      jsonResponse({ items: [], nextCursor: null }),
    );
    renderPage();
    const mount = await screen.findByTestId("knowledge-summary");
    expect(mount).toHaveAttribute("data-mount", "knowledge-summary");
    expect(
      await within(mount).findByText(/还没有关联知识库/),
    ).toBeInTheDocument();
  });
});
