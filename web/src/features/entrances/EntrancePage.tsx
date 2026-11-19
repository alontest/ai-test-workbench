import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { StatusPill } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { PlaceholderPanel } from "./PlaceholderPanel";
import styles from "./entrances.module.css";
import type { Entrance } from "./types";

export function EntrancePage() {
  const { key } = useParams();
  const query = useQuery({
    queryKey: queryKeys.entrances,
    queryFn: () => apiFetch<{ items: Entrance[] }>("/entrances"),
  });

  if (query.isPending) {
    return <Spinner label="加载入口" />;
  }
  if (query.isError || !query.data) {
    return (
      <ErrorState message="无法加载入口" onRetry={() => void query.refetch()} />
    );
  }

  const entrance = query.data.items.find((item) => item.key === key);
  if (!entrance) {
    return (
      <section className={styles.section}>
        <ErrorState message="入口不存在或已被移除" retryable={false} />
        <Link to="/">返回首页</Link>
      </section>
    );
  }

  if (entrance.status === "planned") {
    return <PlaceholderPanel entrance={entrance} />;
  }

  return (
    <section className={styles.section}>
      <p>
        <Link to="/">← 返回首页</Link>
      </p>
      <div data-mount="entrance-live" data-testid="entrance-live" data-entrance={entrance.key}>
        <h1>{entrance.name}</h1>
        <StatusPill status="live" />
      </div>
    </section>
  );
}
