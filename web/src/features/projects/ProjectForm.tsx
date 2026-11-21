import { FormField } from "../../components/ui/FormField";
import { Input, Textarea } from "../../components/ui/Input";
import type { ProjectDraft } from "./types";

export interface ProjectFormProps {
  value: ProjectDraft;
  onChange: (next: ProjectDraft) => void;
  errors: Partial<Record<keyof ProjectDraft, string>>;
}

export function ProjectForm({ value, onChange, errors }: ProjectFormProps) {
  function patch<K extends keyof ProjectDraft>(key: K, next: ProjectDraft[K]) {
    onChange({ ...value, [key]: next });
  }
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <FormField label="项目名称" required error={errors.name}>
        <Input
          value={value.name}
          onChange={(event) => patch("name", event.target.value)}
        />
      </FormField>
      <FormField
        label="仓库地址（自由备注）"
        error={errors.repoUrl}
        hint="人工备注，实际拉取以下方「仓库绑定」为准（AMB-030）"
      >
        <Input
          value={value.repoUrl}
          onChange={(event) => patch("repoUrl", event.target.value)}
        />
      </FormField>
      <FormField label="技术栈" error={errors.techStack}>
        <Input
          value={value.techStack}
          onChange={(event) => patch("techStack", event.target.value)}
        />
      </FormField>
      <FormField label="需求来源" error={errors.requirementSource}>
        <Input
          value={value.requirementSource}
          onChange={(event) => patch("requirementSource", event.target.value)}
        />
      </FormField>
      <FormField label="备注" error={errors.notes}>
        <Textarea
          value={value.notes}
          onChange={(event) => patch("notes", event.target.value)}
        />
      </FormField>
    </div>
  );
}
