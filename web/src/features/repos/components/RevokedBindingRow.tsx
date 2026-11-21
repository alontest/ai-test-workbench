import { Button } from "../../../components/ui/Button";
import type { RepoBindingSummary } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./repo.module.css";
import { RepoStatusBadge } from "./RepoStatusBadge";
import { SyncRecordTable } from "./SyncRecordTable";

export interface RevokedBindingRowProps {
  binding: RepoBindingSummary;
  onViewSnapshot: (bindingId: string) => void;
  onRebind: (binding: RepoBindingSummary) => void;
}

export function RevokedBindingRow({
  binding,
  onViewSnapshot,
  onRebind,
}: RevokedBindingRowProps) {
  return (
    <article className={`${styles.bindingRow} ${styles.revokedRow}`} data-testid="binding-row">
      <div className={styles.bindingMain}>
        <div className={styles.rowMeta}>
          <span className={styles.providerTag}>{PROVIDER_LABELS[binding.provider]}</span>
          <span className={styles.mono}>{binding.repoName}</span>
          <RepoStatusBadge status="revoked" />
        </div>
        <div className={styles.rowMeta}>
          <span>令牌 —</span>
          <span>解绑于 {formatTimestamp(binding.revokedAt)}</span>
        </div>
        <p className={styles.muted}>
          已解绑：快照只读可查，目录树与文件读取不可用；历史会话与调用记录未修改。
        </p>
      </div>
      <div className={styles.rowActions}>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onViewSnapshot(binding.bindingId)}
        >
          查看快照
        </Button>
        <Button type="button" variant="ghost" onClick={() => onRebind(binding)}>
          重新绑定
        </Button>
        <SyncRecordTable bindingId={binding.bindingId} />
      </div>
    </article>
  );
}
