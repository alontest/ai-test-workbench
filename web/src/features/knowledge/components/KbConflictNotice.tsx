import type { ConflictSource } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./knowledge.module.css";

export interface KbConflictNoticeProps {
  conflicts: ConflictSource[];
  variant?: "list" | "detail";
}

const MAX_SOURCES = 20;

export function KbConflictNotice({
  conflicts,
  variant = "detail",
}: KbConflictNoticeProps) {
  if (conflicts.length === 0) {
    return null;
  }
  const shown = conflicts.slice(0, MAX_SOURCES);
  return (
    <div className={styles.stack} data-variant={variant}>
      <p className={styles.banner}>
        同编号在其他来源存在不同摘要：只提示，不阻止注入。
      </p>
      <ul className={styles.reasonList}>
        {shown.map((source) => (
          <li key={`${source.kbName}-${source.version}`}>
            {source.kbName} v{source.version} · 生成于{" "}
            {formatTimestamp(source.generatedAt)}
          </li>
        ))}
      </ul>
    </div>
  );
}
