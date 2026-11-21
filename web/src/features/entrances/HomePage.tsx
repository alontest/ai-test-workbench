import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { Mascot } from "../../components/mascot/Mascot";
import {
  PageContainer,
  PageHeader,
} from "../../components/ui/PageHeader";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { SessionSummary } from "../sessions/types";
import { EntranceGrid } from "./EntranceGrid";
import { RecentSessionTable } from "./RecentSessionTable";
import styles from "./entrances.module.css";
import type { Entrance } from "./types";

interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function HomePage() {
  const entrancesQuery = useQuery({
    queryKey: queryKeys.entrances,
    queryFn: () => apiFetch<{ items: Entrance[] }>("/entrances"),
  });
  const sessionsQuery = useQuery({
    queryKey: queryKeys.sessions({ limit: 10 }),
    queryFn: () =>
      apiFetch<Page<SessionSummary>>(`/sessions${queryString({ limit: 10 })}`),
  });

  const entrances = entrancesQuery.data?.items ?? [];
  const liveCount = entrances.filter((item) => item.status === "live").length;

  return (
    <PageContainer tier="lg" className={styles.home}>
      <PageHeader
        title="开始一次分析"
        description="选项目 → 给输入 → 发起调用，三步拿到 AI 结果。"
        actions={
          <div className={styles.heroAside}>
            <Mascot
              size={56}
              state={entrancesQuery.isError ? "warning" : "idle"}
              label="鸮鸮"
            />
            {!entrancesQuery.isPending && !entrancesQuery.isError ? (
              <p className={styles.preflight}>
                <span className={styles.dot} aria-hidden="true" />
                {liveCount > 0
                  ? `前置检查通过：${entrances.length} 个入口，${liveCount} 个已可用`
                  : `前置检查通过：${entrances.length} 个入口已登记，均在规划中`}
              </p>
            ) : null}
          </div>
        }
      />

      {entrancesQuery.isPending ? (
        <Spinner label="加载入口" />
      ) : entrancesQuery.isError || !entrancesQuery.data ? (
        <ErrorState
          message="无法加载入口"
          onRetry={() => void entrancesQuery.refetch()}
        />
      ) : (
        <EntranceGrid entrances={entrances} />
      )}

      <header className={styles.row}>
        <h2>最近会话</h2>
        <Link to="/sessions">查看全部</Link>
      </header>
      {sessionsQuery.isPending ? (
        <Spinner label="加载会话" />
      ) : sessionsQuery.isError ? (
        <ErrorState
          message="会话列表加载失败"
          onRetry={() => void sessionsQuery.refetch()}
        />
      ) : (
        <RecentSessionTable sessions={sessionsQuery.data?.items ?? []} />
      )}
    </PageContainer>
  );
}
