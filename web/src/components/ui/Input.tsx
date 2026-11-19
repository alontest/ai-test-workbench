import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react";
import styles from "./ui.module.css";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export function Input({ invalid, className, ...props }: InputProps) {
  return (
    <input
      className={[styles.input, className].filter(Boolean).join(" ")}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export function Textarea({ invalid, className, ...props }: TextareaProps) {
  return (
    <textarea
      className={[styles.textarea, className].filter(Boolean).join(" ")}
      aria-invalid={invalid || undefined}
      {...props}
    />
  );
}
