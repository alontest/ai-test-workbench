import { Badge } from "../../../components/ui/Badge";
import { Button } from "../../../components/ui/Button";
import { EmptyState } from "../../../components/ui/Feedback";
import { Skeleton } from "../../../components/ui/Loading";
import type { KnowledgeBaseSummary } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./knowledge.module.css";

export interface KnowledgeBaseTableProps {
  items: KnowledgeBaseSummary[];
  loading: boolean;
  onBrowse: (kbId: string) => void;
  onDelete: (kb: KnowledgeBaseSummary) => void;
}

export function KnowledgeBaseTable({
  items,
  loading,
  onBrowse,
  onDelete,
}: KnowledgeBaseTableProps) {
  if (loading && items.length === 0) {
    return <Skeleton rows={4} />;
  }
  if (items.length === 0) {
    return (
      <EmptyState
        title="还没有知识库"
        description="先在本地生成知识库文件（index.json 与 .md），再导入到项目。"
      />
    );
  }
  return (
    <div className={styles.tableWrap}>
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>项目</th>
            <th>版本</th>
            <th>生成时间</th>
            <th>条目</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.kbId}>
              <td>
                <span className={styles.mono}>{item.name}</span>
                {item.supersededCount > 0 ? (
                  <p className={styles.muted}>
                    另有 {item.supersededCount} 个旧版本（只读）
                  </p>
                ) : null}
              </td>
              <td>{item.project?.name ?? "—"}</td>
              <td>v{item.version}</td>
              <td>{formatTimestamp(item.generatedAt)}</td>
              <td>{item.entryCount.toLocaleString("zh-CN")}</td>
              <td>
                {item.current ? (
                  <Badge label="就绪" tone="success" />
                ) : (
                  <Badge label="旧版本" />
                )}
              </td>
              <td>
                <div className={styles.row}>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onBrowse(item.latestKbId)}
                  >
                    浏览
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onDelete(item)}
                  >
                    删除
                  </Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
