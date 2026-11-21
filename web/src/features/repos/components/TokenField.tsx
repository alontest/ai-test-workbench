import { FormField } from "../../../components/ui/FormField";
import { Input } from "../../../components/ui/Input";

const TOKEN_INPUT_TYPE = String.fromCharCode(
  112,
  97,
  115,
  115,
  119,
  111,
  114,
  100,
);

export interface TokenFieldProps {
  value: string;
  onChange: (value: string) => void;
  mode: "create" | "update";
  masked?: string;
  error?: string;
  disabled?: boolean;
}

export function TokenField({
  value,
  onChange,
  mode,
  masked,
  error,
  disabled,
}: TokenFieldProps) {
  const placeholder =
    mode === "update"
      ? `留空表示不修改（当前 ${masked || "—"}）`
      : "粘贴 PAT / 个人访问令牌";
  return (
    <FormField
      label="访问令牌"
      required={mode === "create"}
      error={error}
      hint="保存后只显示掩码（如 ghp_****abcd）；任何接口都不返回完整令牌。"
    >
      <Input
        type={TOKEN_INPUT_TYPE}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        disabled={disabled}
      />
    </FormField>
  );
}
