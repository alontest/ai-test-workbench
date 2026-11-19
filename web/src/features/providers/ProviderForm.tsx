import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Switch } from "../../components/ui/Switch";
import { ConnectionTestBadge, type ConnectionTestState } from "./ConnectionTestBadge";
import { SecretField } from "./SecretField";
import type { ConnectionTestResult, ProviderDraft } from "./types";

const PROTOCOLS = [
  { value: "openai_compatible", label: "OpenAI 兼容" },
  { value: "anthropic", label: "Anthropic" },
];

export interface ProviderFormProps {
  value: ProviderDraft;
  onChange: (next: ProviderDraft) => void;
  errors: Partial<Record<keyof ProviderDraft, string>>;
  maskedValue?: string;
  testState: ConnectionTestState;
  testResult?: ConnectionTestResult;
  onTest: () => void;
  showEnabled?: boolean;
}

export function ProviderForm({
  value,
  onChange,
  errors,
  maskedValue,
  testState,
  testResult,
  onTest,
  showEnabled,
}: ProviderFormProps) {
  function patch<K extends keyof ProviderDraft>(key: K, next: ProviderDraft[K]) {
    onChange({ ...value, [key]: next });
  }
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <FormField label="名称" required error={errors.name}>
        <Input
          value={value.name}
          onChange={(event) => patch("name", event.target.value)}
        />
      </FormField>
      <FormField label="协议" required error={errors.protocol}>
        <Select
          options={PROTOCOLS}
          value={value.protocol}
          onChange={(next) => patch("protocol", next)}
        />
      </FormField>
      <FormField label="Base URL" required error={errors.baseUrl}>
        <Input
          value={value.baseUrl}
          onChange={(event) => patch("baseUrl", event.target.value)}
        />
      </FormField>
      <SecretField
        maskedValue={maskedValue}
        value={value.apiKey}
        onChange={(next) => patch("apiKey", next)}
        error={errors.apiKey}
      />
      {showEnabled ? (
        <FormField label="启用">
          <Switch
            checked={value.enabled}
            onChange={(checked) => patch("enabled", checked)}
            label="启用提供商"
          />
        </FormField>
      ) : null}
      <ConnectionTestBadge
        state={testState}
        result={testResult}
        onTest={onTest}
      />
    </div>
  );
}
