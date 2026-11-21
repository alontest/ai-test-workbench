import { Link } from "react-router";
import { Mascot } from "../../components/mascot/Mascot";
import { StatusPill } from "../../components/ui/Badge";
import type { SessionSummary } from "../sessions/types";
import styles from "./entrances.module.css";

export interface RecentSessionTableProps {
  sessions: SessionSummary[];
}

export function RecentSessionTable({ sessions }: RecentSessionTableProps) {
  if (sessions.length === 0) {
    return (
      <div className={styles.empty}>
        <Mascot size={96} state="sleeping" label="鸮鸮" />
        <strong>还没有分析会话</strong>
        <p>从入口开始，或先完成项目与模型配置。</p>
        <Link to="/projects">查看项目配置</Link>
      </div>
    );
  }
  return (
    <div className={styles.tableCard}>
      <table className={styles.sessionTable}>
        <thead>
          <tr>
            <th>标题</th>
            <th>项目</th>
            <th>入口</th>
            <th>状态</th>
            <th>更新时间</th>
          </tr>
        </thead>
        <tbody>
          {sessions.map((session) => (
            <tr key={session.sessionId}>
              <td>
                <Link to={`/sessions/${session.sessionId}`}>{session.title}</Link>
              </td>
              <td>{session.project.name}</td>
              <td className={styles.monoCell}>{session.entranceKey}</td>
              <td>
                <StatusPill status={session.status} />
              </td>
              <td className={styles.monoCell}>{session.updatedAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
