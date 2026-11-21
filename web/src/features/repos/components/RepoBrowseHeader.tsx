import { Button } from "../../../components/ui/Button";
import type { RepoBindingSummary } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import styles from "./browse.module.css";
import { RepoBaselineStrip } from "./RepoBaselineStrip";
import { RepoBreadcrumb } from "./RepoBreadcrumb";
import { RepoStatusBadge } from "./RepoStatusBadge";
import { TokenExpiryHint } from "./TokenExpiryHint";

export interface RepoBrowseHeaderProps {
  binding: RepoBindingSummary;
  onRefresh: () => void;
  refreshing?: boolean;
}

export function RepoBrowseHeader({
  binding,
  onRefresh,
  refreshing,
}: RepoBrowseHeaderProps) {
  return (
    <header className={styles.header}>
      <RepoBreadcrumb repoName={binding.repoName} />
      <div className={styles.headerMain}>
        <div className={styles.stack}>
          <h1 className={styles.pageTitle}>{binding.repoName}</h1>
          <div className={styles.rowMeta}>
            <span className={styles.providerTag}>
              {PROVIDER_LABELS[binding.provider]}
            </span>
            <RepoStatusBadge status={binding.status} />
            <TokenExpiryHint expiresAt={binding.tokenExpiresAt} />
            <span className={styles.muted}>
              默认分支{" "}
              <span className={styles.mono}>{binding.defaultBranch ?? "—"}</span> ·
              列表实时读取
            </span>
          </div>
          <RepoBaselineStrip
            lastSyncSuccessAt={binding.lastSyncSuccessAt}
            baseline={binding.baseline}
            revoked={binding.status === "revoked"}
          />
        </div>
        <Button
          type="button"
          variant="secondary"
          onClick={onRefresh}
          loading={refreshing}
          disabled={binding.status === "revoked"}
        >
          刷新
        </Button>
      </div>
    </header>
  );
}
