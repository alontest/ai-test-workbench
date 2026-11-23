import { useState, type ComponentType } from "react";
import { NavLink, Outlet, useLocation } from "react-router";
import {
  FeatureApproval,
  FeatureBugAnalysis,
  FeatureCalls,
  FeatureCaseLibrary,
  FeatureHistory,
  FeatureHome,
  FeatureKnowledge,
  FeatureLogTriage,
  FeatureMcp,
  FeatureProject,
  FeatureProvider,
  FeatureRegressionList,
  FeatureRepo,
  FeatureSession,
  FeatureSkill,
  FeatureSqlAnalysis,
  FeatureTestReport,
  type IconProps,
} from "../components/icons";
import { Mascot } from "../components/mascot/Mascot";
import { Button } from "../components/ui/Button";
import { useLogout } from "../features/auth/useLogout";
import { UnauthorizedBridge } from "./Providers";
import styles from "./AppShell.module.css";

interface EntranceItem {
  key: string;
  name: string;
  icon: ComponentType<IconProps>;
}

const ENTRANCES: readonly EntranceItem[] = [
  { key: "case-library", name: "用例库", icon: FeatureCaseLibrary },
  { key: "regression-list", name: "生成回归清单", icon: FeatureRegressionList },
  { key: "test-report", name: "生成测试报告", icon: FeatureTestReport },
  { key: "bug-analysis", name: "分析 Bug", icon: FeatureBugAnalysis },
  { key: "log-triage", name: "排查日志", icon: FeatureLogTriage },
  { key: "sql-analysis", name: "分析 SQL", icon: FeatureSqlAnalysis },
];

const EXTENSIONS: readonly EntranceItem[] = [
  { key: "skills", name: "QA 技能库", icon: FeatureSkill },
  { key: "mcp", name: "MCP 工具源", icon: FeatureMcp },
  { key: "approvals", name: "审批中心", icon: FeatureApproval },
  { key: "history", name: "变更审计", icon: FeatureHistory },
];

interface NavItem {
  to: string;
  label: string;
  icon: ComponentType<IconProps>;
  end?: boolean;
}

interface NavGroup {
  title: string;
  note?: string;
  items: readonly NavItem[];
}

const NAV_GROUPS: readonly NavGroup[] = [
  {
    title: "工作台",
    items: [
      { to: "/", label: "首页", icon: FeatureHome, end: true },
      { to: "/sessions", label: "分析会话", icon: FeatureSession },
    ],
  },
  {
    title: "测试与诊断",
    items: ENTRANCES.map((item) => ({
      to: `/entrances/${item.key}`,
      label: item.name,
      icon: item.icon,
    })),
  },
  {
    title: "上下文与资产",
    items: [
      { to: "/projects", label: "项目上下文", icon: FeatureProject },
      { to: "/knowledge-bases", label: "知识库", icon: FeatureKnowledge },
      { to: "/repos", label: "代码仓库", icon: FeatureRepo },
      { to: "/extensions/skills", label: "QA 技能库", icon: FeatureSkill },
      { to: "/extensions/mcp", label: "MCP 工具源", icon: FeatureMcp },
    ],
  },
  {
    title: "治理与系统",
    items: [
      { to: "/extensions/approvals", label: "审批中心", icon: FeatureApproval },
      { to: "/extensions/history", label: "变更审计", icon: FeatureHistory },
      { to: "/calls", label: "调用记录", icon: FeatureCalls },
      { to: "/providers", label: "AI 提供商与模型", icon: FeatureProvider },
    ],
  },
];

/** 顶栏位置面包屑：路径 → 层级文字。与页面内 <h1> 不重复。 */
function resolveBreadcrumb(pathname: string): string[] {
  const entranceKey = /^\/entrances\/([^/]+)\/?$/.exec(pathname)?.[1];
  if (entranceKey) {
    const name = ENTRANCES.find((item) => item.key === entranceKey)?.name;
    return ["测试与诊断", name ?? "入口"];
  }
  const extensionKey = /^\/extensions\/([^/]+)\/?$/.exec(pathname)?.[1];
  if (extensionKey) {
    const name = EXTENSIONS.find((item) => item.key === extensionKey)?.name;
    const group =
      extensionKey === "skills" || extensionKey === "mcp"
        ? "上下文与资产"
        : "治理与系统";
    return [group, name ?? "扩展能力"];
  }
  if (pathname === "/") {
    return ["工作台", "首页"];
  }
  if (pathname === "/sessions") {
    return ["工作台", "分析会话"];
  }
  if (/^\/sessions\/[^/]+\/?$/.test(pathname)) {
    return ["工作台", "分析会话", "会话详情"];
  }
  if (pathname === "/providers") {
    return ["治理与系统", "AI 提供商"];
  }
  if (/^\/providers\/[^/]+\/models\/?$/.test(pathname)) {
    return ["治理与系统", "AI 提供商", "模型绑定"];
  }
  if (pathname === "/projects") {
    return ["上下文与资产", "项目上下文"];
  }
  if (/^\/projects\/[^/]+\/repos\/[^/]+\/?$/.test(pathname)) {
    return ["上下文与资产", "项目上下文", "代码仓库"];
  }
  if (pathname === "/calls") {
    return ["治理与系统", "调用记录"];
  }
  if (pathname === "/repos") {
    return ["上下文与资产", "代码仓库"];
  }
  if (pathname === "/knowledge-bases") {
    return ["上下文与资产", "知识库"];
  }
  if (pathname === "/knowledge-bases/import") {
    return ["上下文与资产", "知识库", "导入"];
  }
  if (/^\/knowledge-bases\/[^/]+\/entries\/[^/]+\/?$/.test(pathname)) {
    return ["上下文与资产", "知识库", "条目详情"];
  }
  if (/^\/knowledge-bases\/[^/]+\/?$/.test(pathname)) {
    return ["上下文与资产", "知识库", "知识库详情"];
  }
  return ["工作台"];
}

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const logout = useLogout();
  const crumbs = resolveBreadcrumb(useLocation().pathname);
  const closeDrawer = () => setDrawerOpen(false);

  return (
    <div className={styles.shell}>
      <UnauthorizedBridge />
      <aside
        className={[styles.sidebar, drawerOpen ? styles.sidebarOpen : ""]
          .filter(Boolean)
          .join(" ")}
        data-width="248"
      >
        <div className={styles.brand}>
          <Mascot size={28} state="idle" className={styles.brandMark} />
          <span className={styles.brandText}>
            <span className={styles.brandName}>Vigil · 鸮巡</span>
            <span className={styles.brandTagline}>LOCAL INSPECTOR</span>
          </span>
        </div>
        <nav aria-label="主导航" onClick={closeDrawer}>
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className={styles.navGroup}>
              <h2>
                {group.title}
                {group.note ? (
                  <span className={styles.navTagInline}>{group.note}</span>
                ) : null}
              </h2>
              {group.items.map(({ to, label, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end}>
                  <Icon size={18} className={styles.navIcon} />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      {drawerOpen ? (
        <button
          type="button"
          className={styles.sidebarOverlay}
          aria-label="关闭导航"
          onClick={closeDrawer}
        />
      ) : null}
      <header className={styles.topbar}>
        <Button
          type="button"
          variant="ghost"
          className={styles.menuButton}
          aria-label="打开导航"
          onClick={() => setDrawerOpen((open) => !open)}
        >
          菜单
        </Button>
        <nav aria-label="面包屑" className={styles.breadcrumb}>
          <ol className={styles.crumbList}>
            {crumbs.map((crumb, index) => {
              const isLast = index === crumbs.length - 1;
              return (
                <li key={crumb} className={styles.crumbItem}>
                  {index > 0 ? (
                    <span className={styles.crumbSeparator} aria-hidden="true">
                      /
                    </span>
                  ) : null}
                  <span
                    className={styles.crumb}
                    aria-current={isLast ? "page" : undefined}
                  >
                    {crumb}
                  </span>
                </li>
              );
            })}
          </ol>
        </nav>
        <Button
          type="button"
          variant="ghost"
          onClick={() => logout.mutate()}
          loading={logout.isPending}
        >
          退出
        </Button>
      </header>
      <main className={styles.content}>
        <Outlet />
      </main>
    </div>
  );
}
