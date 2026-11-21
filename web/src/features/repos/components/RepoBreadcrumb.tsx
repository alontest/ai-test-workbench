import { Link } from "react-router";
import styles from "./browse.module.css";

export interface RepoBreadcrumbProps {
  repoName: string | null;
}

export function RepoBreadcrumb({ repoName }: RepoBreadcrumbProps) {
  return (
    <nav className={styles.breadcrumb} aria-label="面包屑">
      <Link to="/projects">← 返回项目上下文</Link>
      <span aria-hidden="true">/</span>
      <span className={styles.mono}>{repoName ?? "—"}</span>
    </nav>
  );
}
