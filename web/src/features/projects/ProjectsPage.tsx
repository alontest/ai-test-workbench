import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { ProjectDialog } from "./ProjectDialog";
import { ProjectKnowledgeSummary } from "./ProjectKnowledgeSummary";
import { ProjectList } from "./ProjectList";
import type { Project } from "./types";

interface PageResponse {
  items: Project[];
  nextCursor: string | null;
}

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Project | undefined>();
  const [creating, setCreating] = useState(false);
  const query = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<PageResponse>("/projects"),
  });

  if (query.isPending) {
    return <Spinner label="加载项目" />;
  }
  if (query.isError) {
    return (
      <ErrorState
        message="无法加载项目列表"
        onRetry={() => void query.refetch()}
      />
    );
  }

  return (
    <section>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>项目上下文</h1>
        <Button type="button" onClick={() => setCreating(true)}>
          新建项目
        </Button>
      </header>
      <ProjectKnowledgeSummary />
      <ProjectList projects={query.data.items} onEdit={setEditing} />
      {creating || editing ? (
        <ProjectDialog
          open
          project={editing}
          onClose={() => {
            setCreating(false);
            setEditing(undefined);
          }}
          onSaved={() => {
            void queryClient.invalidateQueries({ queryKey: queryKeys.projects });
          }}
        />
      ) : null}
    </section>
  );
}
