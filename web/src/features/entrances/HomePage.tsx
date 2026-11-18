import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
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

  return (
    <section className={styles.section}>
      <h1>工作台</h1>
      {entrancesQuery.isPending ? (
        <Spinner label="加载入口" />
      ) : entrancesQuery.isError || !entrancesQuery.data ? (
        <ErrorState
          message="无法加载入口"
          onRetry={() => void entrancesQuery.refetch()}
        />
      ) : (
        <EntranceGrid entrances={entrancesQuery.data.items} />
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
    </section>
  );
}
