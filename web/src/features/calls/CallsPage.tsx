import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { Project } from "../projects/types";
import type { SessionSummary } from "../sessions/types";
import { CallFilters, defaultCallFilters, toRfc3339 } from "./CallFilters";
import { CallRecordTable } from "./CallRecordTable";
import styles from "./calls.module.css";
import type { CallFiltersValue, CallRecord } from "./types";

interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export function CallsPage() {
  const [filters, setFilters] = useState<CallFiltersValue>(defaultCallFilters);
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<Page<Project>>("/projects"),
  });
  const sessionsQuery = useQuery({
    queryKey: queryKeys.sessions({
      projectId: filters.projectId ? Number(filters.projectId) : undefined,
    }),
    queryFn: () =>
      apiFetch<Page<SessionSummary>>(
        `/sessions${queryString({
          projectId: filters.projectId ? Number(filters.projectId) : undefined,
        })}`,
      ),
  });
  const callParams = useMemo(
    () => ({
      projectId: filters.projectId ? Number(filters.projectId) : undefined,
      sessionId: filters.sessionId ? Number(filters.sessionId) : undefined,
      status: filters.status || undefined,
      from: toRfc3339(filters.from),
      to: toRfc3339(filters.to),
    }),
    [filters],
  );
  const callsQuery = useQuery({
    queryKey: [...queryKeys.calls, callParams],
    queryFn: () =>
      apiFetch<Page<CallRecord>>(`/calls${queryString(callParams)}`),
  });
  const filtered = Boolean(
    filters.projectId || filters.sessionId || filters.status,
  );

  return (
    <PageContainer tier="xl" className={styles.page}>
      <PageHeader
        title="调用记录"
        description="按项目、会话、状态与时间范围核对每次模型调用的输入摘要、耗时与知识注入；记录只读留痕，不保存密钥。"
      />
      <CallFilters
        value={filters}
        onChange={setFilters}
        projects={projectsQuery.data?.items ?? []}
        sessions={sessionsQuery.data?.items ?? []}
      />
      <CallRecordTable
        calls={callsQuery.data?.items ?? []}
        loading={callsQuery.isPending}
        error={callsQuery.isError ? "无法加载调用记录" : undefined}
        onRetry={() => void callsQuery.refetch()}
        filtered={filtered}
      />
    </PageContainer>
  );
}
