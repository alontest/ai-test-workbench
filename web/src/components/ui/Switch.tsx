import { Switch as RadixSwitch } from "radix-ui";
import styles from "./ui.module.css";

export interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
}

export function Switch({ checked, onChange, disabled, label }: SwitchProps) {
  return (
    <RadixSwitch.Root
      className={styles.switch}
      checked={checked}
      onCheckedChange={onChange}
      disabled={disabled}
      aria-label={label}
    >
      <RadixSwitch.Thumb className={styles.thumb} />
    </RadixSwitch.Root>
  );
}
