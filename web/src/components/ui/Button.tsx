import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./ui.module.css";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  loading?: boolean;
  children: ReactNode;
}

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  const variantClass =
    variant === "secondary"
      ? styles.buttonSecondary
      : variant === "ghost"
        ? styles.buttonGhost
        : variant === "danger"
          ? styles.buttonDanger
          : "";
  return (
    <button
      className={[styles.button, variantClass, className].filter(Boolean).join(" ")}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {children}
    </button>
  );
}
