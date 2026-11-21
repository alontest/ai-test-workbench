import { ConfirmDialog } from "../../../components/ui/ConfirmDialog";
import type { KnowledgeBaseSummary } from "../api/types";

export interface KbDeleteDialogProps {
  open: boolean;
  kb: KnowledgeBaseSummary | null;
  affectedVersions: number;
  entryCount: number;
  fileCount: number;
  loading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function KbDeleteDialog({
  open,
  kb,
  affectedVersions,
  entryCount,
  fileCount,
  loading,
  onConfirm,
  onCancel,
}: KbDeleteDialogProps) {
  return (
    <ConfirmDialog
      open={open}
      title="删除知识库？"
      danger
      confirmLabel="删除"
      loading={loading}
      onConfirm={onConfirm}
      onCancel={onCancel}
      description={
        <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
          <p style={{ margin: 0 }}>
            删除后不可恢复。历史会话与调用记录不变，相关编号将标注「知识库已删除」。将同时删除：
          </p>
          <ul style={{ margin: 0, paddingLeft: "var(--spacing-5)" }}>
            <li>
              知识库「{kb?.name ?? ""}」及其全部版本（{affectedVersions} 个）
            </li>
            <li>条目索引（{entryCount.toLocaleString("zh-CN")} 条）</li>
            <li>已存文件（{fileCount.toLocaleString("zh-CN")} 个）</li>
            <li>项目与该知识库的关联</li>
          </ul>
        </div>
      }
    />
  );
}
