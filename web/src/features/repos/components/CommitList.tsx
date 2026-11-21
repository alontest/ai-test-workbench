import { Button } from "../../../components/ui/Button";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import type { CommitSummary } from "../api/types";
import styles from "./browse.module.css";
import { CommitRow } from "./CommitRow";

export interface CommitListProps {
  items: CommitSummary[];
  loading: boolean;
  error?: boolean;
  hasMore: boolean;
  loadingMore?: boolean;
  onLoadMore: () => void;
  onRetry?: () => void;
}

export function CommitList({
  items,
  loading,
  error,
  hasMore,
  loadingMore,
  onLoadMore,
  onRetry,
}: CommitListProps) {
  if (loading && items.length === 0) {
    return <Spinner label="加载提交" />;
  }
  if (error) {
    return <ErrorState message="提交列表加载失败" onRetry={onRetry} />;
  }
  if (items.length === 0) {
    return <EmptyState title="没有提交" description="当前分支暂无提交；可切换分支或刷新。" />;
  }
  return (
    <div>
      <div className={styles.commitList}>
        {items.map((commit) => (
          <CommitRow key={commit.sha} commit={commit} />
        ))}
      </div>
      <div className={styles.pager} data-testid="commit-pager">
        <span>已加载 {items.length} 条 · 按时间倒序</span>
        {hasMore ? (
          <Button
            type="button"
            variant="ghost"
            loading={loadingMore}
            onClick={onLoadMore}
          >
            加载下一页
          </Button>
        ) : (
          <span className={styles.muted}>已加载全部</span>
        )}
      </div>
    </div>
  );
}
