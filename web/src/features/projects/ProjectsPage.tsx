import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { RepoBindingPanel } from "../repos/components/RepoBindingPanel";
import { ProjectDialog } from "./ProjectDialog";
import { ProjectKnowledgeSummary } from "./ProjectKnowledgeSummary";
import { ProjectList } from "./ProjectList";
import styles from "./projects.module.css";
import type { Project } from "./types";

interface PageResponse {
  items: Project[];
  nextCursor: string | null;
}

export function ProjectsPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<Project | undefined>();
  const [creating, setCreating] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const query = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<PageResponse>("/projects"),
  });

  return (
    <PageContainer tier="xl" className={styles.page}>
      <PageHeader
        title="项目上下文"
        description="左侧选择项目，右侧查看仓库绑定与同步基线；项目级只读资产，不克隆仓库、不建立代码索引。"
        actions={
          <Button type="button" onClick={() => setCreating(true)}>
            新建项目
          </Button>
        }
      />
      <ProjectKnowledgeSummary />
      <div className={styles.workbench}>
        <section className={styles.master} aria-label="项目列表">
          {query.isPending ? (
            <div className={styles.stateCard}>
              <Spinner label="加载项目" />
            </div>
          ) : query.isError ? (
            <div className={styles.stateCard}>
              <ErrorState
                message="无法加载项目列表"
                onRetry={() => void query.refetch()}
              />
            </div>
          ) : (
            <ProjectList
              projects={query.data.items}
              onEdit={setEditing}
              onSelect={(project) => setSelectedId(project.projectId)}
              selectedId={selectedId}
            />
          )}
        </section>
        <section className={styles.detail} aria-label="仓库绑定工作区">
          <RepoBindingPanel projectId={selectedId} />
        </section>
      </div>
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
    </PageContainer>
  );
}
