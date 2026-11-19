import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { Project } from "../projects/types";
import { CreateSessionDialog } from "./CreateSessionDialog";
import { SessionFilters, type SessionFiltersValue } from "./SessionFilters";
import { SessionTable } from "./SessionTable";
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
    <section>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>会话</h1>
        <Button type="button" onClick={() => setCreating(true)}>
          新建会话
        </Button>
      </header>
      <SessionFilters
        value={filters}
        onChange={setFilters}
        projects={projectsQuery.data?.items ?? []}
      />
      {query.isPending ? (
        <Spinner label="加载会话" />
      ) : query.isError ? (
        <ErrorState message="无法加载会话" onRetry={() => void query.refetch()} />
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
    </section>
  );
}
