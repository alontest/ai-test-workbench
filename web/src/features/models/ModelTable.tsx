import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/Feedback";
import { Switch } from "../../components/ui/Switch";
import styles from "./models.module.css";
import type { ModelBinding } from "./types";

export interface ModelTableProps {
  models: ModelBinding[];
  onEdit: (model: ModelBinding) => void;
  onToggle: (model: ModelBinding, enabled: boolean) => void;
}

export function ModelTable({ models, onEdit, onToggle }: ModelTableProps) {
  if (models.length === 0) {
    return (
      <div className={styles.emptyCard}>
        <EmptyState title="还没有模型" description="为该提供商登记一个模型。" />
      </div>
    );
  }
  return (
    <div className={styles.tableCard}>
      <table>
        <thead>
          <tr>
            <th>模型名</th>
            <th>显示名</th>
            <th>temperature</th>
            <th>max_tokens</th>
            <th>启用</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {models.map((model) => (
            <tr key={model.modelId}>
              <td className={styles.modelName}>{model.modelName}</td>
              <td className={styles.displayName}>{model.displayName}</td>
              <td>
                <span className={styles.paramPill}>{model.defaultTemperature}</span>
              </td>
              <td>
                <span className={styles.paramPill}>
                  {model.defaultMaxTokens.toLocaleString("en-US")}
                </span>
              </td>
              <td>
                <Switch
                  checked={model.enabled}
                  onChange={(enabled) => onToggle(model, enabled)}
                  label={`启用 ${model.modelName}`}
                />
              </td>
              <td>
                <div className={styles.actions}>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onEdit(model)}
                  >
                    编辑
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
