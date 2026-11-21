import { useState } from "react";
import { Button } from "../../../components/ui/Button";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import { useRepoTree } from "../hooks/useRepoBrowse";
import styles from "./browse.module.css";
import { TreeNode } from "./TreeNode";
import { TreeTruncatedNote } from "./TreeTruncatedNote";

export interface RepoTreeProps {
  bindingId: string;
  repoId: string | null;
  ref: string | null;
  path?: string;
  depth?: number;
  disabled?: boolean;
  onOpenFile: (path: string) => void;
}

/**
 * 逐级目录树：每一层按 path 单独查询，展开子目录时再请求下一层。
 * `hasMore` 追加加载，`truncated` 只渲染固定提示，两者互不冒充。
 */
export function RepoTree({
  bindingId,
  repoId,
  ref,
  path = "",
  depth = 0,
  disabled,
  onOpenFile,
}: RepoTreeProps) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const query = useRepoTree(bindingId, repoId, ref, path, {
    enabled: !disabled,
  });
  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const truncated = query.data?.pages.some((page) => page.truncated) ?? false;

  if (disabled) {
    return (
      <p className={styles.readonlyNote}>
        已解绑：目录树入口置灰，不发起任何供应商请求。
      </p>
    );
  }
  if (query.isPending) {
    return <Spinner label="加载目录" />;
  }
  if (query.isError) {
    return (
      <ErrorState
        message="目录树加载失败"
        onRetry={() => void query.refetch()}
      />
    );
  }
  if (items.length === 0 && !query.hasNextPage) {
    return <EmptyState title="空目录" description="当前路径没有条目。" />;
  }

  function toggle(entryPath: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(entryPath)) {
        next.delete(entryPath);
      } else {
        next.add(entryPath);
      }
      return next;
    });
  }

  return (
    <div className={styles.tree} data-testid="repo-tree">
      {items.map((entry) => {
        const isExpanded = expanded.has(entry.path);
        return (
          <div key={entry.path}>
            <TreeNode
              entry={entry}
              depth={depth}
              expanded={isExpanded}
              onToggle={() => toggle(entry.path)}
              onOpen={() => onOpenFile(entry.path)}
            />
            {entry.type === "dir" && isExpanded ? (
              <RepoTree
                bindingId={bindingId}
                repoId={repoId}
                ref={ref}
                path={entry.path}
                depth={depth + 1}
                onOpenFile={onOpenFile}
              />
            ) : null}
          </div>
        );
      })}
      {query.hasNextPage ? (
        <div className={styles.treeMore}>
          <Button
            type="button"
            variant="ghost"
            loading={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
          >
            加载下一页
          </Button>
        </div>
      ) : null}
      <TreeTruncatedNote visible={truncated} />
    </div>
  );
}
