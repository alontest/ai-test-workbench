import { useState } from "react";
import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import type { RepoSyncRecord } from "../api/types";
import { formatDuration, formatTimestamp } from "../format";
import { useSyncRecords } from "../hooks/useRepoBindings";
import styles from "./repo.module.css";

export interface SyncRecordTableProps {
  bindingId: string;
  onToggle?: (open: boolean) => void;
}

function statusTone(status: RepoSyncRecord["status"]) {
  if (status === "success") {
    return "success" as const;
  }
  if (status === "running") {
    return "info" as const;
  }
  return "danger" as const;
}

function recordNote(record: RepoSyncRecord): string {
  if (record.status === "success") {
    return `仓库 ${record.repoCount ?? 0} · 分支 ${record.branchCount ?? 0} · 提交 ${
      record.commitCount ?? 0
    }`;
  }
  const parts: string[] = [];
  if (record.errorCategory) {
    parts.push(record.errorCategory);
  }
  if (record.errorMessage) {
    parts.push(record.errorMessage);
  }
  if (record.retryAfterAt) {
    parts.push(`限流至 ${formatTimestamp(record.retryAfterAt)}`);
  }
  parts.push("保留上次成功基线与时间");
  return parts.join(" · ");
}

export function SyncRecordTable({ bindingId, onToggle }: SyncRecordTableProps) {
  const [open, setOpen] = useState(false);
  const query = useSyncRecords(bindingId, open);
  const records = query.data?.pages.flatMap((page) => page.items) ?? [];

  function toggle() {
    const next = !open;
    setOpen(next);
    onToggle?.(next);
  }

  return (
    <div className={styles.syncRecords}>
      <Button
        type="button"
        variant="ghost"
        onClick={toggle}
        aria-expanded={open}
      >
        {open ? "收起同步记录" : "查看同步记录"}
      </Button>
      {open ? (
        <div data-testid="sync-records">
          {query.isPending ? (
            <Spinner label="加载同步记录" />
          ) : query.isError ? (
            <ErrorState
              message="无法加载同步记录"
              onRetry={() => void query.refetch()}
            />
          ) : records.length === 0 ? (
            <p className={styles.muted}>还没有同步记录。</p>
          ) : (
            <div className={styles.tableWrap}>
              <table>
                <thead>
                  <tr>
                    <th>开始时间</th>
                    <th>耗时</th>
                    <th>结果</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record) => (
                    <tr key={record.syncId}>
                      <td className={styles.mono}>
                        {formatTimestamp(record.startedAt)}
                      </td>
                      <td>{formatDuration(record.durationMs)}</td>
                      <td>
                        <Badge
                          label={
                            record.status === "success"
                              ? "成功"
                              : record.status === "running"
                                ? "进行中"
                                : "失败"
                          }
                          tone={statusTone(record.status)}
                        />
                      </td>
                      <td className={styles.muted}>{recordNote(record)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {query.hasNextPage ? (
            <Button
              type="button"
              variant="ghost"
              loading={query.isFetchingNextPage}
              onClick={() => void query.fetchNextPage()}
            >
              加载更多
            </Button>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
