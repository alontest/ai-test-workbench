import type { RepoBaseline } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./repo.module.css";

export interface RepoBaselineStripProps {
  lastSyncSuccessAt: string | null;
  baseline?: RepoBaseline | null;
  revoked?: boolean;
}

export function RepoBaselineStrip({
  lastSyncSuccessAt,
  baseline,
  revoked,
}: RepoBaselineStripProps) {
  if (!lastSyncSuccessAt && !baseline) {
    return (
      <p className={styles.baseline} data-testid="repo-baseline">
        从未同步
      </p>
    );
  }
  return (
    <p className={styles.baseline} data-testid="repo-baseline">
      上次同步基线{" "}
      {baseline?.ref ? (
        <span className={styles.mono}>
          {baseline.ref} @ {baseline.sha ?? "—"}
        </span>
      ) : (
        "—"
      )}{" "}
      · {formatTimestamp(baseline?.fetchedAt ?? lastSyncSuccessAt)} · 仅作对照
      {revoked ? "与失效时的 last-known" : ""}
    </p>
  );
}
