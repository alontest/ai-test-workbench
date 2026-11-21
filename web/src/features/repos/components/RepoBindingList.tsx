import { EmptyState } from "../../../components/ui/Feedback";
import { Skeleton } from "../../../components/ui/Loading";
import type { RepoBindingSummary } from "../api/types";
import type { BindingBusy } from "./RepoBindingRow";
import { RepoBindingRow } from "./RepoBindingRow";
import { RevokedBindingRow } from "./RevokedBindingRow";
import styles from "./repo.module.css";

export interface RepoBindingListProps {
  bindings: RepoBindingSummary[];
  loading: boolean;
  busy?: { bindingId: string; kind: BindingBusy } | null;
  onTest: (bindingId: string) => void;
  onSync: (bindingId: string) => void;
  onBrowse: (bindingId: string) => void;
  onUpdateToken: (binding: RepoBindingSummary) => void;
  onUnbind: (binding: RepoBindingSummary) => void;
  onRebind: (binding: RepoBindingSummary) => void;
}

export function RepoBindingList({
  bindings,
  loading,
  busy,
  onTest,
  onSync,
  onBrowse,
  onUpdateToken,
  onUnbind,
  onRebind,
}: RepoBindingListProps) {
  if (loading && bindings.length === 0) {
    return <Skeleton rows={3} />;
  }
  if (bindings.length === 0) {
    return (
      <EmptyState
        title="还没有绑定仓库"
        description="绑定后可测试连接并同步分支与提交；未同步时浏览为空态。"
      />
    );
  }
  const active = bindings.filter((binding) => binding.status !== "revoked");
  const revoked = bindings.filter((binding) => binding.status === "revoked");
  return (
    <div className={styles.bindingList}>
      {active.map((binding) => (
        <RepoBindingRow
          key={binding.bindingId}
          binding={binding}
          busy={
            busy?.bindingId === binding.bindingId ? busy.kind : undefined
          }
          onTest={onTest}
          onSync={onSync}
          onBrowse={onBrowse}
          onUpdateToken={onUpdateToken}
          onUnbind={onUnbind}
        />
      ))}
      {revoked.map((binding) => (
        <RevokedBindingRow
          key={binding.bindingId}
          binding={binding}
          onViewSnapshot={onBrowse}
          onRebind={onRebind}
        />
      ))}
    </div>
  );
}
