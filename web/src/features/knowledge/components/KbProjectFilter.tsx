import { Select } from "../../../components/ui/Select";
import styles from "./knowledge.module.css";

export interface KbProjectFilterProps {
  value: number | null;
  onChange: (projectId: number | null) => void;
  projects: { id: number; name: string }[];
}

export function KbProjectFilter({
  value,
  onChange,
  projects,
}: KbProjectFilterProps) {
  return (
    <label className={styles.stack}>
      <span className={styles.muted}>项目</span>
      <Select
        aria-label="项目筛选"
        value={value === null ? "" : String(value)}
        placeholder="全部项目"
        options={projects.map((project) => ({
          value: String(project.id),
          label: project.name,
        }))}
        onChange={(next) => onChange(next === "" ? null : Number(next))}
      />
    </label>
  );
}
