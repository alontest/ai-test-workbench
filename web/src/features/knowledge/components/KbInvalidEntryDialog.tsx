import { ConfirmDialog } from "../../../components/ui/ConfirmDialog";
import type { InvalidItem } from "../api/types";
import { invalidReasonLabel } from "../format";
import styles from "./knowledge.module.css";

export interface KbInvalidEntryDialogProps {
  open: boolean;
  invalidItems: InvalidItem[];
  validCount: number;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function KbInvalidEntryDialog({
  open,
  invalidItems,
  validCount,
  loading,
  onConfirm,
  onCancel,
}: KbInvalidEntryDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      title="部分条目不可用，是否继续？"
      confirmLabel="继续调用"
      loading={loading}
      onConfirm={onConfirm}
      onCancel={onCancel}
      description={
        <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
          <p style={{ margin: 0 }}>以下编号已被剔除，不会注入本次调用：</p>
          <ul className={styles.reasonList}>
            {invalidItems.map((item) => (
              <li key={`${item.kbId}-${item.code}`}>
                <code>{item.code}</code> · {invalidReasonLabel(item.reason)}
              </li>
            ))}
          </ul>
          <p style={{ margin: 0 }}>
            其余 {validCount} 条有效条目将照常注入并产生调用记录。
          </p>
          <p className={styles.muted}>
            取消后不会发起调用，也不会产生调用记录。
          </p>
        </div>
      }
    />
  );
}
