import { ErrorState, EmptyState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { CallRecordRow } from "./CallRecordRow";
import type { CallRecord } from "./types";

export interface CallRecordTableProps {
  calls: CallRecord[];
  loading?: boolean;
  error?: string;
  onRetry?: () => void;
  filtered?: boolean;
}

export function CallRecordTable({
  calls,
  loading,
  error,
  onRetry,
  filtered,
}: CallRecordTableProps) {
  if (loading) {
    return <Spinner label="加载调用记录" />;
  }
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }
  if (calls.length === 0) {
    return (
      <EmptyState
        title={
          filtered ? "没有符合筛选条件的调用记录" : "还没有调用记录"
        }
        description={
          filtered
            ? "试试清除筛选条件或扩大时间范围。"
            : "发起调用后会在这里留下可核对的记录。"
        }
      />
    );
  }
  return (
    <table>
      <thead>
        <tr>
          <th>模型</th>
          <th>状态</th>
          <th>耗时</th>
          <th>次数</th>
          <th>时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        {calls.map((call) => (
          <CallRecordRow key={call.callId} call={call} />
        ))}
      </tbody>
    </table>
  );
}
