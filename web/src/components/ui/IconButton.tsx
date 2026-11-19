import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./ui.module.css";

export interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  icon?: ReactNode;
}

export function IconButton({ label, icon, className, ...props }: IconButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      className={[styles.button, styles.buttonGhost, styles.iconButton, className]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {icon ?? label}
    </button>
  );
}
