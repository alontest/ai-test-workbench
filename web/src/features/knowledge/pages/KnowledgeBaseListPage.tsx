import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router";
import { FeatureKnowledge } from "../../../components/icons";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/Feedback";
import { PageContainer, PageHeader } from "../../../components/ui/PageHeader";
import { apiFetch } from "../../../lib/api/client";
import { queryKeys } from "../../../lib/api/keys";
import type { KnowledgeBaseSummary } from "../api/types";
import { KbDeleteDialog } from "../components/KbDeleteDialog";
import { KbProjectFilter } from "../components/KbProjectFilter";
import { KnowledgeBaseTable } from "../components/KnowledgeBaseTable";
import { useDeleteKnowledge } from "../hooks/useDeleteKnowledge";
import { useKnowledgeBases } from "../hooks/useKnowledgeBases";
import styles from "../components/knowledge.module.css";

interface ProjectPage {
  items: { projectId: number; name: string }[];
  nextCursor: string | null;
}

export function KnowledgeBaseListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const projectParam = searchParams.get("projectId");
  const parsedProject = projectParam ? Number(projectParam) : undefined;
  const projectId =
    parsedProject !== undefined && Number.isFinite(parsedProject)
      ? parsedProject
      : undefined;
  const [deleting, setDeleting] = useState<KnowledgeBaseSummary | null>(null);

  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<ProjectPage>("/projects"),
  });
  const query = useKnowledgeBases(projectId);
  const deleteMutation = useDeleteKnowledge();

  const items = query.data?.pages.flatMap((page) => page.items) ?? [];

  function onProjectChange(next: number | null) {
    const params = new URLSearchParams(searchParams);
    if (next === null) {
      params.delete("projectId");
    } else {
      params.set("projectId", String(next));
    }
    setSearchParams(params, { replace: true });
  }

  return (
    <PageContainer tier="xl" className={styles.page}>
      <PageHeader
        title="知识库"
        description="项目级只读资产：导入后可在浏览页按编号查看，并在会话调用时注入。"
        actions={
          <Button
            type="button"
            onClick={() => navigate("/knowledge-bases/import")}
          >
            导入知识库
          </Button>
        }
      />

      <div className={styles.toolbar}>
        <KbProjectFilter
          value={projectId ?? null}
          onChange={onProjectChange}
          projects={(projectsQuery.data?.items ?? []).map((project) => ({
            id: project.projectId,
            name: project.name,
          }))}
        />
        <span className={styles.muted}>
          共 {items.length} 个知识库
          {query.hasNextPage ? "（可分页加载）" : ""}
        </span>
      </div>

      {deleteMutation.isError ? (
        <p className={styles.bannerError} role="alert">
          删除失败，请重试。
        </p>
      ) : null}

      {query.isError ? (
        <ErrorState
          message="无法加载知识库列表"
          onRetry={() => void query.refetch()}
        />
      ) : (
        <KnowledgeBaseTable
          items={items}
          loading={query.isPending}
          onBrowse={(kbId) => navigate(`/knowledge-bases/${kbId}`)}
          onDelete={setDeleting}
        />
      )}

      {query.hasNextPage ? (
        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            loading={query.isFetchingNextPage}
            onClick={() => void query.fetchNextPage()}
          >
            加载更多
          </Button>
        </div>
      ) : null}

      <p className={styles.footerTip}>
        <FeatureKnowledge size={16} />
        <span>
          只读导入：工作台不修改上传文件，也不在线编辑条目；同名重新导入会生成新版本，旧版本只读保留。
        </span>
      </p>

      <KbDeleteDialog
        open={deleting !== null}
        kb={deleting}
        affectedVersions={deleting ? Math.max(deleting.version, 1) : 0}
        entryCount={deleting?.entryCount ?? 0}
        fileCount={deleting?.fileCount ?? 0}
        loading={deleteMutation.isPending}
        onCancel={() => setDeleting(null)}
        onConfirm={() => {
          if (!deleting) {
            return;
          }
          deleteMutation.mutate(deleting.kbId, {
            onSettled: () => setDeleting(null),
          });
        }}
      />
    </PageContainer>
  );
}
