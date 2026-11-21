import { ProviderBrand } from "../../../components/icons";
import { Mascot } from "../../../components/mascot/Mascot";
import { Button } from "../../../components/ui/Button";
import { PageHeader } from "../../../components/ui/PageHeader";
import type { RepoBindingSummary } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import styles from "./browse.module.css";
import { RepoBaselineStrip } from "./RepoBaselineStrip";
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
  const revoked = binding.status === "revoked";
  return (
    <div className={styles.header}>
      <PageHeader
        backLink={{ to: "/projects", label: "返回项目上下文" }}
        title={
          <span className={styles.repoTitle}>
            <ProviderBrand provider={binding.provider} size={22} />
            <span>{binding.repoName}</span>
          </span>
        }
        badge={<RepoStatusBadge status={binding.status} />}
        actions={
          <Button
            type="button"
            variant="secondary"
            onClick={onRefresh}
            loading={refreshing}
            disabled={revoked}
          >
            刷新
          </Button>
        }
      />
      <div className={styles.headerMeta}>
        <span className={styles.providerTag}>
          {PROVIDER_LABELS[binding.provider]}
        </span>
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
        revoked={revoked}
      />
      {revoked ? (
        <div className={styles.revokedHint}>
          <Mascot size={48} state="sleeping" />
          <span>绑定已解绑，仅可查看上次同步基线，不再发起供应商请求。</span>
        </div>
      ) : null}
    </div>
  );
}
