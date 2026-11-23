import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { describe, expect, test } from "vitest";
import { PLANNED_EXTENSIONS } from "./catalog";
import { PlannedExtensionPage } from "./PlannedExtensionPage";

function renderExtension(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/extensions/:key" element={<PlannedExtensionPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("PlannedExtensionPage 平台扩展占位页", () => {
  test.each(PLANNED_EXTENSIONS)(
    "渲染 $name（/extensions/$key）的规划简报与红线",
    (item) => {
      renderExtension(`/extensions/${item.key}`);
      expect(
        screen.getByRole("heading", { level: 1, name: item.name }),
      ).toBeInTheDocument();
      expect(
        screen.getByText(new RegExp(item.capabilityId)),
      ).toBeInTheDocument();
      expect(screen.getByText(item.summary)).toBeInTheDocument();
      for (const rule of item.guardrails) {
        expect(screen.getByText(rule)).toBeInTheDocument();
      }
      expect(
        screen.getByRole("link", { name: "前往分析会话" }),
      ).toHaveAttribute("href", "/sessions");
    },
  );

  test("未知 key 显示未规划错误态", () => {
    renderExtension("/extensions/unknown");
    expect(screen.getByText("扩展能力不存在或尚未规划")).toBeInTheDocument();
  });
});
