import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";

export interface AdvancedParamsValue {
  temperature: string;
  maxTokens: string;
}

export interface AdvancedParamsProps {
  value: AdvancedParamsValue;
  onChange: (next: AdvancedParamsValue) => void;
  disabled?: boolean;
}

export function AdvancedParams({
  value,
  onChange,
  disabled = false,
}: AdvancedParamsProps) {
  return (
    <div style={{ display: "grid", gap: "var(--spacing-3)" }}>
      <FormField label="temperature" hint="本次覆盖，不写回模型默认">
        <Input
          inputMode="decimal"
          value={value.temperature}
          disabled={disabled}
          onChange={(event) =>
            onChange({ ...value, temperature: event.target.value })
          }
        />
      </FormField>
      <FormField label="max_tokens" hint="本次覆盖，不写回模型默认">
        <Input
          inputMode="numeric"
          value={value.maxTokens}
          disabled={disabled}
          onChange={(event) =>
            onChange({ ...value, maxTokens: event.target.value })
          }
        />
      </FormField>
    </div>
  );
}
