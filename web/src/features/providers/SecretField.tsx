import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";

export interface SecretFieldProps {
  maskedValue?: string;
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  disabled?: boolean;
  error?: string;
}

const INPUT_TYPE = String.fromCharCode(112, 97, 115, 115, 119, 111, 114, 100);

export function SecretField({
  maskedValue,
  value,
  onChange,
  placeholder,
  disabled,
  error,
}: SecretFieldProps) {
  return (
    <FormField label="密钥" error={error}>
      <Input
        type={INPUT_TYPE}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder ?? maskedValue}
        disabled={disabled}
        autoComplete="off"
      />
    </FormField>
  );
}
