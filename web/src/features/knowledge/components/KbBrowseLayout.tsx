import type { ReactNode } from "react";
import { Link } from "react-router";
import type { KbVersionItem } from "../api/types";
import { formatTimestamp } from "../format";
import { KbVersionSelector } from "./KbVersionSelector";
import styles from "./knowledge.module.css";

export interface KbBrowseLayoutProps {
  title: string;
  version: number;
  generatedAt: string | null;
  superseded: boolean;
  currentKbId: string;
  latestKbId: string;
  versions: KbVersionItem[];
  onSelectVersion: (kbId: string) => void;
  toolbar?: ReactNode;
  children: ReactNode;
}

export function KbBrowseLayout({
  title,
  version,
  generatedAt,
  superseded,
  currentKbId,
  latestKbId,
  versions,
  onSelectVersion,
  toolbar,
  children,
}: KbBrowseLayoutProps) {
  return (
    <section className={styles.page}>
      <div className={styles.pageHead}>
        <div className={styles.stack}>
          <h1 style={{ margin: 0 }}>{title}</h1>
          <p className={styles.muted}>
            v{version} · 生成于 {formatTimestamp(generatedAt)}
          </p>
        </div>
        <KbVersionSelector
          versions={versions}
          currentKbId={currentKbId}
          onChange={onSelectVersion}
        />
      </div>
      {superseded ? (
        <p className={styles.banner} role="status">
          当前查看的是旧版本，已被新版本取代。
          <Link to={`/knowledge-bases/${latestKbId}`}>查看最新版</Link>
        </p>
      ) : null}
      {toolbar}
      {children}
    </section>
  );
}
