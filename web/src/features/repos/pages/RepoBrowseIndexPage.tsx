import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import {
  IconChevronRight,
  ProviderBrand,
} from "../../../components/icons";
import { ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../../components/ui/PageHeader";
import { apiFetch } from "../../../lib/api/client";
import { queryKeys } from "../../../lib/api/keys";
import type { Project } from "../../projects/types";
import { PROVIDER_LABELS } from "../api/types";
import styles from "../components/browse.module.css";
import { useRepoBindings } from "../hooks/useRepoBindings";

interface ProjectPage {
  items: Project[];
  nextCursor: string | null;
}

function ProjectBindings({
  projectId,
  name,
}: {
  projectId: number;
  name: string;
}) {
  const query = useRepoBindings(projectId);
  const bindings =
    query.data?.pages
      .flatMap((page) => page.items)
      .filter((binding) => binding.status !== "revoked") ?? [];

  return (
    <section className={styles.card} aria-label={`${name} 的仓库绑定`}>
      <div className={styles.sectionHead}>
        <h2 className={styles.cardTitle}>{name}</h2>
        {bindings.length > 0 ? (
          <span className={styles.muted}>{bindings.length} 个仓库</span>
        ) : null}
      </div>
      {query.isPending ? (
        <Spinner label="加载绑定" />
      ) : query.isError ? (
        <p className={styles.muted}>无法加载该项目的仓库绑定。</p>
      ) : bindings.length === 0 ? (
        <p className={styles.muted}>
          还没有绑定仓库。<Link to="/projects">去项目上下文添加</Link>
        </p>
      ) : (
        <ul className={styles.repoBindingList}>
          {bindings.map((binding) => (
            <li key={binding.bindingId}>
              <Link
                className={styles.repoBindingRow}
                to={`/projects/${projectId}/repos/${binding.bindingId}`}
              >
                <ProviderBrand provider={binding.provider} size={20} />
                <span className={styles.repoBindingMain}>
                  <span className={styles.repoBindingName}>
                    {binding.repoName}
                  </span>
                  <span className={styles.muted}>
                    {PROVIDER_LABELS[binding.provider]}
                  </span>
                </span>
                <span className={styles.monoPill}>
                  {binding.defaultBranch ?? "无默认分支"}
                </span>
                <span
                  className={styles.statusDot}
                  data-status={binding.status}
                  aria-hidden="true"
                />
                <IconChevronRight size={16} className={styles.chevron} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function RepoBrowseIndexPage() {
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<ProjectPage>("/projects"),
  });

  const projects = projectsQuery.data?.items ?? [];

  return (
    <PageContainer tier="lg" className={styles.page}>
      <PageHeader
        title="仓库浏览"
        description="从项目上下文选择一个仓库绑定，进入实时目录树、提交与按需文件查看。"
      />

      {projectsQuery.isPending ? (
        <Spinner label="加载项目" />
      ) : projectsQuery.isError ? (
        <ErrorState
          message="无法加载项目列表"
          onRetry={() => void projectsQuery.refetch()}
        />
      ) : projects.length === 0 ? (
        <p className={styles.muted}>
          还没有项目。<Link to="/projects">先创建项目上下文</Link>
        </p>
      ) : (
        <div className={styles.projectGrid}>
          {projects.map((project) => (
            <ProjectBindings
              key={project.projectId}
              projectId={project.projectId}
              name={project.name}
            />
          ))}
        </div>
      )}
    </PageContainer>
  );
}
