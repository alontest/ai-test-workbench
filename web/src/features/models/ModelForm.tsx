import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";
import { Switch } from "../../components/ui/Switch";
import type { ModelDraft } from "./types";

export interface ModelFormProps {
  value: ModelDraft;
  onChange: (next: ModelDraft) => void;
  errors: Partial<Record<keyof ModelDraft, string>>;
  nameLocked?: boolean;
}

export function ModelForm({
  value,
  onChange,
  errors,
  nameLocked,
}: ModelFormProps) {
  function patch<K extends keyof ModelDraft>(key: K, next: ModelDraft[K]) {
    onChange({ ...value, [key]: next });
  }
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <FormField label="模型名" required error={errors.modelName}>
        <Input
          value={value.modelName}
          onChange={(event) => patch("modelName", event.target.value)}
          disabled={nameLocked}
        />
      </FormField>
      <FormField label="显示名" required error={errors.displayName}>
        <Input
          value={value.displayName}
          onChange={(event) => patch("displayName", event.target.value)}
        />
      </FormField>
      <FormField label="temperature" error={errors.defaultTemperature}>
        <Input
          type="number"
          step="0.01"
          min={0}
          max={2}
          value={value.defaultTemperature}
          onChange={(event) => patch("defaultTemperature", event.target.value)}
        />
      </FormField>
      <FormField label="max_tokens" error={errors.defaultMaxTokens}>
        <Input
          type="number"
          min={1}
          max={1000000}
          value={value.defaultMaxTokens}
          onChange={(event) => patch("defaultMaxTokens", event.target.value)}
        />
      </FormField>
      {nameLocked ? (
        <FormField label="启用">
          <Switch
            checked={value.enabled}
            onChange={(checked) => patch("enabled", checked)}
            label="启用模型"
          />
        </FormField>
      ) : null}
    </div>
  );
}
