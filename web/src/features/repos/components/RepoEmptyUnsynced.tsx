import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/Feedback";
import styles from "./browse.module.css";

export interface RepoEmptyUnsyncedProps {
  variant: "browse" | "commits" | "tree";
  onSync: () => void;
  syncing?: boolean;
}

const COPY: Record<
  RepoEmptyUnsyncedProps["variant"],
  { title: string; description: string }
> = {
  browse: {
    title: "还没有可浏览的元数据",
    description:
      "先执行一次同步，刷新仓库、分支与提交基线后再浏览；未同步不返回错误页。",
  },
  commits: {
    title: "还没有提交基线",
    description: "同步后会缓存最近 100 条提交；实时读取需要可用的令牌。",
  },
  tree: {
    title: "还没有目录基线",
    description: "同步后可逐级浏览目录；目录内容始终实时读取。",
  },
};

export function RepoEmptyUnsynced({
  variant,
  onSync,
  syncing,
}: RepoEmptyUnsyncedProps) {
  const copy = COPY[variant];
  return (
    <div className={styles.emptyCard}>
      <EmptyState
        title={copy.title}
        description={copy.description}
        action={
          <Button type="button" onClick={onSync} loading={syncing}>
            去同步
          </Button>
        }
      />
    </div>
  );
}
