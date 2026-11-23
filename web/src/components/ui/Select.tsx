import type { SelectHTMLAttributes } from "react";
import styles from "./ui.module.css";

interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "onChange"> {
  options: SelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  invalid?: boolean;
}

export function Select({
  options,
  value,
  onChange,
  placeholder,
  invalid,
  className,
  ...props
}: SelectProps) {
  return (
    <select
      className={[styles.select, className].filter(Boolean).join(" ")}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-invalid={invalid || undefined}
      {...props}
    >
      {placeholder ? (
        <option value="">{placeholder}</option>
      ) : null}
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
