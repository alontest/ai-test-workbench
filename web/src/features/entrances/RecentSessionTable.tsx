import { Link } from "react-router";
import { EmptyState } from "../../components/ui/Feedback";
import { StatusPill } from "../../components/ui/Badge";
import type { SessionSummary } from "../sessions/types";

export interface RecentSessionTableProps {
  sessions: SessionSummary[];
}

export function RecentSessionTable({ sessions }: RecentSessionTableProps) {
  if (sessions.length === 0) {
    return (
      <EmptyState
        title="还没有分析会话"
        description="从入口开始，或先完成项目与模型配置。"
        action={
          <Link to="/projects">查看项目配置</Link>
        }
      />
    );
  }
  return (
    <table>
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
            <td>{session.entranceKey}</td>
            <td>
              <StatusPill status={session.status} />
            </td>
            <td>{session.updatedAt}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
