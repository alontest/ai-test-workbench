import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/Feedback";
import type { Project } from "./types";

export interface ProjectListProps {
  projects: Project[];
  onEdit: (project: Project) => void;
}

export function ProjectList({ projects, onEdit }: ProjectListProps) {
  if (projects.length === 0) {
    return <EmptyState title="还没有项目" description="创建一个项目上下文后再发起会话。" />;
  }
  return (
    <table>
      <thead>
        <tr>
          <th>名称</th>
          <th>技术栈</th>
          <th>更新时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {projects.map((project) => (
          <tr key={project.projectId}>
            <td>{project.name}</td>
            <td>{project.techStack ?? "—"}</td>
            <td>{project.updatedAt}</td>
            <td>
              <Button type="button" variant="ghost" onClick={() => onEdit(project)}>
                编辑
              </Button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
