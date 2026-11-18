import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { Button } from "../components/ui/Button";
import { useLogout } from "../features/auth/useLogout";
import { UnauthorizedBridge } from "./Providers";
import styles from "./AppShell.module.css";

const ENTRANCES = [
  { key: "case-library", name: "用例库" },
  { key: "bug-analysis", name: "分析 bug" },
  { key: "log-triage", name: "排查日志" },
  { key: "sql-analysis", name: "分析 SQL" },
  { key: "regression-list", name: "生成回归清单" },
  { key: "test-report", name: "生成测试报告" },
];

export function AppShell() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const logout = useLogout();

  return (
    <div className={styles.shell}>
      <UnauthorizedBridge />
      <aside
        className={[styles.sidebar, drawerOpen ? styles.sidebarOpen : ""]
          .filter(Boolean)
          .join(" ")}
        data-width="248"
      >
        <nav aria-label="主导航">
          <div className={styles.navGroup}>
            <h2>工作台</h2>
            <NavLink to="/" end>
              首页
            </NavLink>
            <NavLink to="/sessions">会话</NavLink>
          </div>
          <div className={styles.navGroup}>
            <h2>入口</h2>
            {ENTRANCES.map((item) => (
              <NavLink key={item.key} to={`/entrances/${item.key}`}>
                {item.name}
              </NavLink>
            ))}
          </div>
          <div className={styles.navGroup}>
            <h2>基座管理</h2>
            <NavLink to="/projects">项目上下文</NavLink>
            <NavLink to="/providers">AI 提供商与模型</NavLink>
            <NavLink to="/calls">调用记录</NavLink>
          </div>
        </nav>
      </aside>
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
        <strong>AI 测试工作台</strong>
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
