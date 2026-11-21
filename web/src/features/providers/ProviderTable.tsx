import { Link } from "react-router";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/Feedback";
import { Switch } from "../../components/ui/Switch";
import styles from "./providers.module.css";
import type { Provider } from "./types";

export interface ProviderTableProps {
  providers: Provider[];
  onEdit: (provider: Provider) => void;
  onToggle: (provider: Provider, enabled: boolean) => void;
}

export function ProviderTable({ providers, onEdit, onToggle }: ProviderTableProps) {
  if (providers.length === 0) {
    return (
      <div className={styles.emptyCard}>
        <EmptyState title="还没有提供商" description="先登记一个 AI 提供商。" />
      </div>
    );
  }
  return (
    <div className={styles.tableCard}>
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>协议</th>
            <th>密钥</th>
            <th>启用</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {providers.map((provider) => (
            <tr key={provider.providerId}>
              <td className={styles.nameCell}>{provider.name}</td>
              <td>
                <span className={styles.protocolPill}>{provider.protocol}</span>
              </td>
              <td>
                <span className={styles.maskedKey}>{provider.apiKeyMasked}</span>
              </td>
              <td>
                <Switch
                  checked={provider.enabled}
                  onChange={(enabled) => onToggle(provider, enabled)}
                  label={`启用 ${provider.name}`}
                />
              </td>
              <td>
                <div className={styles.actions}>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => onEdit(provider)}
                  >
                    编辑
                  </Button>
                  <Link
                    className={styles.linkButton}
                    to={`/providers/${provider.providerId}/models`}
                  >
                    模型
                  </Link>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
