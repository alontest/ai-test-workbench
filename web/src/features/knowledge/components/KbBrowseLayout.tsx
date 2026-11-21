import type { ReactNode } from "react";
import { Link } from "react-router";
import { PageHeader } from "../../../components/ui/PageHeader";
import type { KbVersionItem } from "../api/types";
import { formatTimestamp } from "../format";
import { KbVersionSelector } from "./KbVersionSelector";
import styles from "./knowledge.module.css";

export interface KbBrowseLayoutProps {
  title: string;
  version: number | null;
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
    <>
      <PageHeader
        backLink={{ to: "/knowledge-bases", label: "知识库" }}
        title={title}
        badge={
          version !== null ? (
            <span className={styles.versionPill}>v{version}</span>
          ) : undefined
        }
        description={
          version !== null
            ? `v${version} · 生成于 ${formatTimestamp(generatedAt)}`
            : "按编号、类型与关键词浏览知识条目。"
        }
        actions={
          versions.length > 0 ? (
            <KbVersionSelector
              versions={versions}
              currentKbId={currentKbId}
              onChange={onSelectVersion}
            />
          ) : undefined
        }
      />
      {superseded ? (
        <p className={styles.bannerWarn} role="status">
          当前查看的是旧版本，已被新版本取代。
          <Link to={`/knowledge-bases/${latestKbId}`}>查看最新版</Link>
        </p>
      ) : null}
      {toolbar}
      {children}
    </>
  );
}
