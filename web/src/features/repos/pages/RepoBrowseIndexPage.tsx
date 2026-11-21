import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
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
      <h2 className={styles.cardTitle}>{name}</h2>
      {query.isPending ? (
        <Spinner label="加载绑定" />
      ) : query.isError ? (
        <p className={styles.muted}>无法加载该项目的仓库绑定。</p>
      ) : bindings.length === 0 ? (
        <p className={styles.muted}>
          还没有绑定仓库。<Link to="/projects">去项目上下文添加</Link>
        </p>
      ) : (
        <ul className={styles.linkList}>
          {bindings.map((binding) => (
            <li key={binding.bindingId}>
              <Link to={`/projects/${projectId}/repos/${binding.bindingId}`}>
                <span className={styles.mono}>{binding.repoName}</span>
              </Link>
              <span className={styles.muted}>
                {" "}
                · {PROVIDER_LABELS[binding.provider]} ·{" "}
                {binding.defaultBranch ?? "无默认分支"}
              </span>
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

  if (projectsQuery.isPending) {
    return <Spinner label="加载项目" />;
  }
  if (projectsQuery.isError) {
    return (
      <ErrorState
        message="无法加载项目列表"
        onRetry={() => void projectsQuery.refetch()}
      />
    );
  }

  const projects = projectsQuery.data.items;
  return (
    <section className={styles.page}>
      <div className={styles.stack}>
        <h1 className={styles.pageTitle}>仓库浏览</h1>
        <p className={styles.muted}>
          从项目上下文选择一个仓库绑定，进入实时目录树、提交与按需文件查看。
        </p>
      </div>
      {projects.length === 0 ? (
        <p className={styles.muted}>
          还没有项目。<Link to="/projects">先创建项目上下文</Link>
        </p>
      ) : (
        <div className={styles.stack}>
          {projects.map((project) => (
            <ProjectBindings
              key={project.projectId}
              projectId={project.projectId}
              name={project.name}
            />
          ))}
        </div>
      )}
    </section>
  );
}
