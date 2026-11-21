import { Button } from "../../../components/ui/Button";
import type { RepoBindingSummary } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import { formatTimestamp } from "../format";
import { RepoBaselineStrip } from "./RepoBaselineStrip";
import styles from "./repo.module.css";
import { RepoStatusBadge } from "./RepoStatusBadge";
import { SyncControl } from "./SyncControl";
import { SyncRecordTable } from "./SyncRecordTable";
import { TokenExpiryHint } from "./TokenExpiryHint";

export type BindingBusy = "testing" | "syncing";

export interface RepoBindingRowProps {
  binding: RepoBindingSummary;
  busy?: BindingBusy;
  onTest: (bindingId: string) => void;
  onSync: (bindingId: string) => void;
  onBrowse: (bindingId: string) => void;
  onUpdateToken: (binding: RepoBindingSummary) => void;
  onUnbind: (binding: RepoBindingSummary) => void;
}

export function RepoBindingRow({
  binding,
  busy,
  onTest,
  onSync,
  onBrowse,
  onUpdateToken,
  onUnbind,
}: RepoBindingRowProps) {
  return (
    <article className={styles.bindingRow} data-testid="binding-row">
      <div className={styles.bindingMain}>
        <div className={styles.rowMeta}>
          <span className={styles.providerTag}>
            {PROVIDER_LABELS[binding.provider]}
          </span>
          <span className={styles.mono}>{binding.repoName}</span>
          <RepoStatusBadge status={busy === "syncing" ? "syncing" : binding.status} />
          <TokenExpiryHint expiresAt={binding.tokenExpiresAt} />
        </div>
        <div className={styles.rowMeta}>
          <span>
            默认分支{" "}
            <span className={styles.mono}>{binding.defaultBranch ?? "—"}</span>
          </span>
          <span>
            令牌{" "}
            <span className={styles.mono} data-testid="binding-mask">
              {binding.tokenMasked || "—"}
            </span>
          </span>
          <span className={styles.mono}>{binding.apiBaseUrl}</span>
        </div>
        <div className={styles.rowMeta}>
          <span>
            上次测试{" "}
            {binding.lastVerifiedAt
              ? `${formatTimestamp(binding.lastVerifiedAt)} · ${
                  binding.lastVerifyResult ?? "未知"
                }`
              : "从未测试"}
          </span>
        </div>
        {binding.status === "token_invalid" ? (
          <p className={styles.dangerText}>
            令牌失效：可查看上次同步基线，重新填写并测试成功即恢复「已连接」。
          </p>
        ) : null}
        <SyncControl
          binding={binding}
          syncing={busy === "syncing"}
          onSync={() => onSync(binding.bindingId)}
        />
        <RepoBaselineStrip
          lastSyncSuccessAt={binding.lastSyncSuccessAt}
          baseline={binding.baseline}
        />
      </div>
      <div className={styles.rowActions}>
        <Button
          type="button"
          variant="secondary"
          onClick={() => onTest(binding.bindingId)}
          loading={busy === "testing"}
          disabled={busy === "syncing"}
        >
          测试连接
        </Button>
        <Button type="button" variant="ghost" onClick={() => onBrowse(binding.bindingId)}>
          浏览
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => onUpdateToken(binding)}
        >
          更新令牌
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => onUnbind(binding)}
          disabled={busy === "syncing"}
        >
          解绑
        </Button>
        <SyncRecordTable bindingId={binding.bindingId} />
      </div>
    </article>
  );
}
