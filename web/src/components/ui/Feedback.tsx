import type { ReactNode } from "react";
import { Button } from "./Button";
import styles from "./ui.module.css";

export interface EmptyStateProps {
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className={styles.feedback}>
      <strong>{title}</strong>
      {description ? <p>{description}</p> : null}
      {action}
    </div>
  );
}

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
  retryable?: boolean;
}

export function ErrorState({ message, onRetry, retryable = true }: ErrorStateProps) {
  return (
    <div className={styles.feedback} role="alert">
      <p>{message}</p>
      {retryable && onRetry ? (
        <Button type="button" variant="secondary" onClick={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}
