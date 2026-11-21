import type { CommitSummary } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./browse.module.css";

export interface CommitRowProps {
  commit: CommitSummary;
}

export function CommitRow({ commit }: CommitRowProps) {
  return (
    <div className={styles.commitRow} data-testid="commit-row">
      <span className={styles.commitSha}>{commit.shortSha ?? commit.sha.slice(0, 7)}</span>
      <div className={styles.commitMain}>
        <span className={styles.commitTitle}>{commit.title ?? "（无标题）"}</span>
        <span className={styles.muted}>
          {commit.authorName ?? "未知作者"} · {formatTimestamp(commit.committedAt)}
        </span>
      </div>
    </div>
  );
}
