import { Link } from "react-router";
import { EmptyState } from "../../components/ui/Feedback";
import uiStyles from "../../components/ui/ui.module.css";
import { SessionDeleteButton } from "./SessionHeader";
import { StatusPill } from "./StatusPill";
import styles from "./SessionsPage.module.css";
import type { SessionSummary } from "./types";

export interface SessionTableProps {
  sessions: SessionSummary[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  filtered?: boolean;
}

export function SessionTable({
  sessions,
  loading,
  error,
  onRetry,
  filtered,
}: SessionTableProps) {
  if (loading) {
    return <p>加载中</p>;
  }
  if (error) {
    return (
      <p role="alert">
        {error}
        {onRetry ? (
          <button type="button" onClick={onRetry}>
            重试
          </button>
        ) : null}
      </p>
    );
  }
  if (sessions.length === 0) {
    return (
      <EmptyState
        title={filtered ? "没有符合筛选条件的会话" : "还没有会话"}
        description={
          filtered ? "试试清除筛选条件。" : "创建一个会话开始调试。"
        }
      />
    );
  }
  return (
    <div className={uiStyles.tableCard}>
      <table>
        <thead>
          <tr>
            <th>标题</th>
            <th>项目</th>
            <th>状态</th>
            <th>模型</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.sessionId}>
              <td>
                <Link className={styles.sessionTitle} to={`/sessions/${session.sessionId}`}>
                  {session.title}
                </Link>
              </td>
              <td>{session.project.name}</td>
              <td>
                <StatusPill status={session.status} />
              </td>
              <td className={styles.modelCell}>{session.model.displayName}</td>
              <td>
                <SessionDeleteButton session={session} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
