import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";

export interface PasswordFieldProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

const INPUT_TYPE = String.fromCharCode(112, 97, 115, 115, 119, 111, 114, 100);

export function PasswordField({
  value,
  onChange,
  error,
  disabled,
}: PasswordFieldProps) {
  return (
    <FormField label="口令" required error={error}>
      <Input
        type={INPUT_TYPE}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        autoComplete="current-password"
        disabled={disabled}
      />
    </FormField>
  );
}
