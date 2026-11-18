import { AlertDialog } from "radix-ui";
import type { ReactNode } from "react";
import { Button } from "./Button";
import styles from "./ui.module.css";

export interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: ReactNode;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
  danger?: boolean;
  loading?: boolean;
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "确认",
  onConfirm,
  onCancel,
  danger,
  loading,
}: ConfirmDialogProps) {
  return (
    <AlertDialog.Root open={open} onOpenChange={(next) => !next && onCancel()}>
      <AlertDialog.Portal>
        <AlertDialog.Overlay className={styles.overlay} />
        <AlertDialog.Content className={styles.content}>
          <AlertDialog.Title>{title}</AlertDialog.Title>
          <AlertDialog.Description asChild>
            <div>{description}</div>
          </AlertDialog.Description>
          <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
            <Button variant="ghost" type="button" onClick={onCancel} disabled={loading}>
              取消
            </Button>
            <Button
              variant={danger ? "danger" : "primary"}
              type="button"
              loading={loading}
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          </div>
        </AlertDialog.Content>
      </AlertDialog.Portal>
    </AlertDialog.Root>
  );
}
