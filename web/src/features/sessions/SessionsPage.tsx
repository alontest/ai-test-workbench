import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import uiStyles from "../../components/ui/ui.module.css";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { Project } from "../projects/types";
import { CreateSessionDialog } from "./CreateSessionDialog";
import { SessionFilters, type SessionFiltersValue } from "./SessionFilters";
import { SessionTable } from "./SessionTable";
import styles from "./SessionsPage.module.css";
import type { SessionSummary } from "./types";

interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function SessionsPage() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [filters, setFilters] = useState<SessionFiltersValue>({
    projectId: "",
    status: "",
  });
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<Page<Project>>("/projects"),
  });
  const query = useQuery({
    queryKey: queryKeys.sessions({
      projectId: filters.projectId ? Number(filters.projectId) : undefined,
      status: filters.status || undefined,
    }),
    queryFn: () =>
      apiFetch<Page<SessionSummary>>(
        `/sessions${queryString({
          projectId: filters.projectId ? Number(filters.projectId) : undefined,
          status: filters.status || undefined,
        })}`,
      ),
  });

  const filtered = Boolean(filters.projectId || filters.status);

  return (
    <PageContainer tier="xl" className={styles.page}>
      <PageHeader
        title="会话"
        description="按项目与状态筛选分析会话；每条会话保留完整调用轨迹与知识注入记录。"
        actions={
          <Button type="button" onClick={() => setCreating(true)}>
            新建会话
          </Button>
        }
      />
      <SessionFilters
        value={filters}
        onChange={setFilters}
        projects={projectsQuery.data?.items ?? []}
      />
      {query.isPending ? (
        <div className={[uiStyles.tableCard, styles.statusCard].join(" ")}>
          <Spinner label="加载会话" />
        </div>
      ) : query.isError ? (
        <div className={uiStyles.tableCard}>
          <ErrorState message="无法加载会话" onRetry={() => void query.refetch()} />
        </div>
      ) : (
        <SessionTable sessions={query.data.items} filtered={filtered} />
      )}
      {creating ? (
        <CreateSessionDialog
          open
          onClose={() => setCreating(false)}
          onCreated={() => {
            void queryClient.invalidateQueries({ queryKey: ["sessions"] });
          }}
        />
      ) : null}
    </PageContainer>
  );
}
