import { ConfirmDialog } from "../../../components/ui/ConfirmDialog";
import type { RepoBindingSummary } from "../api/types";
import styles from "./repo.module.css";

export interface UnbindDialogProps {
  open: boolean;
  binding: RepoBindingSummary | null;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function UnbindDialog({
  open,
  binding,
  loading,
  onConfirm,
  onCancel,
}: UnbindDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      title="撤销仓库绑定？"
      danger
      confirmLabel="确认解绑"
      loading={loading}
      onConfirm={onConfirm}
      onCancel={onCancel}
      description={
        <div className={styles.confirm}>
          <p>
            将撤销 <span className={styles.mono}>{binding?.repoName ?? ""}</span>{" "}
            的绑定与令牌。撤销后：
          </p>
          <ul>
            <li>加密令牌被删除，此后不再发起任何供应商请求；</li>
            <li>仓库 / 分支 / 提交快照保留并标「已解绑」，只读可查；</li>
            <li>目录树与文件读取入口置灰、不可用；</li>
            <li>历史会话、制品与调用记录不变；</li>
            <li>重新绑定同一仓库会生成新的 bindingId 与新令牌。</li>
          </ul>
        </div>
      }
    />
  );
}
