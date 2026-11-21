import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/Feedback";
import styles from "./projects.module.css";
import type { Project } from "./types";

export interface ProjectListProps {
  projects: Project[];
  onEdit: (project: Project) => void;
  onSelect: (project: Project) => void;
  selectedId: number | null;
}

function formatUpdatedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function ProjectList({
  projects,
  onEdit,
  onSelect,
  selectedId,
}: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <div className={styles.emptyCard}>
        <EmptyState
          title="还没有项目"
          description="创建一个项目上下文后再发起会话。"
        />
      </div>
    );
  }
  return (
    <ul className={styles.projectList}>
      {projects.map((project) => {
        const selected = project.projectId === selectedId;
        return (
          <li
            key={project.projectId}
            className={styles.projectRow}
            data-selected={selected || undefined}
          >
            <div className={styles.projectTop}>
              <span className={styles.projectName}>{project.name}</span>
              <span className={styles.techPill}>
                {project.techStack ?? "未填技术栈"}
              </span>
            </div>
            <div className={styles.projectBottom}>
              <span className={styles.updatedAt}>
                更新 {formatUpdatedAt(project.updatedAt)}
              </span>
              <div className={styles.projectActions}>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onSelect(project)}
                >
                  {selected ? "已选择" : "仓库绑定"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => onEdit(project)}
                >
                  编辑
                </Button>
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
