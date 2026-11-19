import { FormField } from "../../components/ui/FormField";
import { Select } from "../../components/ui/Select";
import type { Project } from "../projects/types";

export interface SessionFiltersValue {
  projectId: string;
  status: string;
}

export interface SessionFiltersProps {
  value: SessionFiltersValue;
  onChange: (next: SessionFiltersValue) => void;
  projects: Project[];
}

export function SessionFilters({
  value,
  onChange,
  projects,
}: SessionFiltersProps) {
  return (
    <div style={{ display: "flex", gap: 12 }}>
      <FormField label="项目">
        <Select
          options={projects.map((project) => ({
            value: String(project.projectId),
            label: project.name,
          }))}
          value={value.projectId}
          onChange={(projectId) => onChange({ ...value, projectId })}
          placeholder="全部项目"
        />
      </FormField>
      <FormField label="状态">
        <Select
          options={[
            { value: "in_progress", label: "进行中" },
            { value: "completed", label: "已完成" },
            { value: "failed", label: "失败" },
          ]}
          value={value.status}
          onChange={(status) => onChange({ ...value, status })}
          placeholder="全部状态"
        />
      </FormField>
    </div>
  );
}
