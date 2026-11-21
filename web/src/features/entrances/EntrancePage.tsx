import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router";
import { StatusPill } from "../../components/ui/Badge";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { PlaceholderPanel } from "./PlaceholderPanel";
import styles from "./entrances.module.css";
import type { Entrance } from "./types";

const BACK_LINK = { to: "/", label: "返回首页" } as const;

export function EntrancePage() {
  const { key } = useParams();
  const query = useQuery({
    queryKey: queryKeys.entrances,
    queryFn: () => apiFetch<{ items: Entrance[] }>("/entrances"),
  });

  if (query.isPending) {
    return (
      <PageContainer tier="md" className={styles.section}>
        <PageHeader
          backLink={BACK_LINK}
          title="入口"
          description="正在读取入口配置…"
        />
        <Spinner label="加载入口" />
      </PageContainer>
    );
  }
  if (query.isError || !query.data) {
    return (
      <PageContainer tier="md" className={styles.section}>
        <PageHeader
          backLink={BACK_LINK}
          title="入口"
          description="入口配置暂时无法读取。"
        />
        <ErrorState
          message="无法加载入口"
          onRetry={() => void query.refetch()}
        />
      </PageContainer>
    );
  }

  const entrance = query.data.items.find((item) => item.key === key);
  if (!entrance) {
    return (
      <PageContainer tier="md" className={styles.section}>
        <PageHeader
          backLink={BACK_LINK}
          title="入口"
          description="请返回首页选择其他入口。"
        />
        <ErrorState message="入口不存在或已被移除" retryable={false} />
      </PageContainer>
    );
  }

  return (
    <PageContainer tier="md" className={styles.section}>
      <PageHeader
        backLink={BACK_LINK}
        title={entrance.name}
        description={entrance.description}
        badge={<StatusPill status={entrance.status} />}
      />
      {entrance.status === "planned" ? (
        <PlaceholderPanel entrance={entrance} />
      ) : (
        <div
          data-mount="entrance-live"
          data-testid="entrance-live"
          data-entrance={entrance.key}
        >
          入口已启用。
        </div>
      )}
    </PageContainer>
  );
}
