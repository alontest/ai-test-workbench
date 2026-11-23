import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import type { Project } from "../projects/types";
import type { SessionSummary } from "../sessions/types";
import styles from "./calls.module.css";
import type { CallFiltersValue } from "./types";

const DEFAULT_RANGE_MS = 7 * 24 * 60 * 60 * 1000;

export function defaultCallFilters(): CallFiltersValue {
  const now = new Date();
  return {
    projectId: "",
    sessionId: "",
    status: "",
    from: toDatetimeLocalValue(new Date(now.getTime() - DEFAULT_RANGE_MS)),
    to: toDatetimeLocalValue(now),
  };
}

function toDatetimeLocalValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function toRfc3339(local: string): string | undefined {
  if (!local) {
    return undefined;
  }
  const date = new Date(local);
  if (Number.isNaN(date.getTime())) {
    return undefined;
  }
  return date.toISOString();
}

export interface CallFiltersProps {
  value: CallFiltersValue;
  onChange: (next: CallFiltersValue) => void;
  projects: Project[];
  sessions: SessionSummary[];
}

export function CallFilters({
  value,
  onChange,
  projects,
  sessions,
}: CallFiltersProps) {
  const sessionOptions = sessions
    .filter(
      (session) =>
        !value.projectId || String(session.project.projectId) === value.projectId,
    )
    .map((session) => ({
      value: String(session.sessionId),
      label: session.title,
    }));

  return (
    <div className={styles.filters}>
      <FormField label="项目">
        <Select
          options={projects.map((project) => ({
            value: String(project.projectId),
            label: project.name,
          }))}
          value={value.projectId}
          onChange={(projectId) =>
            onChange({ ...value, projectId, sessionId: "" })
          }
          placeholder="全部项目"
        />
      </FormField>
      <FormField label="会话">
        <Select
          options={sessionOptions}
          value={value.sessionId}
          onChange={(sessionId) => onChange({ ...value, sessionId })}
          placeholder={value.projectId ? "全部会话" : "请先选择项目"}
          disabled={!value.projectId}
        />
      </FormField>
      <FormField label="状态">
        <Select
          options={[
            { value: "success", label: "成功" },
            { value: "failed", label: "失败" },
            { value: "timeout", label: "超时" },
          ]}
          value={value.status}
          onChange={(status) => onChange({ ...value, status })}
          placeholder="全部状态"
        />
      </FormField>
      <FormField label="开始时间">
        <Input
          type="datetime-local"
          value={value.from}
          onChange={(event) => onChange({ ...value, from: event.target.value })}
        />
      </FormField>
      <FormField label="结束时间">
        <Input
          type="datetime-local"
          value={value.to}
          onChange={(event) => onChange({ ...value, to: event.target.value })}
        />
      </FormField>
      <div className={styles.filterActions}>
        <Button
          type="button"
          variant="ghost"
          onClick={() => onChange(defaultCallFilters())}
        >
          清除筛选
        </Button>
      </div>
    </div>
  );
}
