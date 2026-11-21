import { Button } from "../../../components/ui/Button";
import type { RepoBindingSummary } from "../api/types";
import { formatDuration, formatTimestamp } from "../format";
import styles from "./repo.module.css";

export interface SyncControlProps {
  binding: RepoBindingSummary;
  syncing: boolean;
  onSync: () => void;
}

export function SyncControl({ binding, syncing, onSync }: SyncControlProps) {
  const revoked = binding.status === "revoked";
  const lastAttempt = binding.lastSyncAttemptAt;
  const failed = binding.lastSyncStatus === "failed";
  return (
    <div className={styles.syncControl}>
      <div className={styles.actionsInline}>
        <Button
          type="button"
          onClick={onSync}
          loading={syncing}
          disabled={revoked || syncing}
        >
          {syncing ? "同步中…" : "同步"}
        </Button>
        <span className={styles.muted} data-testid="sync-summary">
          {lastAttempt
            ? `上次同步 ${formatTimestamp(lastAttempt)} · ${formatDuration(
                binding.lastSyncDurationMs,
              )}`
            : "从未同步"}
        </span>
      </div>
      {failed ? (
        <p className={styles.bannerWarning} role="status">
          同步失败
          {binding.lastSyncErrorCategory
            ? `（${binding.lastSyncErrorCategory}）`
            : ""}
          {binding.lastSyncErrorMessage ? `：${binding.lastSyncErrorMessage}` : "。"}
          {binding.lastSyncRetryAfter
            ? ` 限流至 ${formatTimestamp(binding.lastSyncRetryAfter)}。`
            : ""}
          已保留上次成功基线与时间
          {binding.lastSyncSuccessAt
            ? `（${formatTimestamp(binding.lastSyncSuccessAt)}）`
            : ""}
          。
        </p>
      ) : null}
    </div>
  );
}
