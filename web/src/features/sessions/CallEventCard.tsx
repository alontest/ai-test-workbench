import { Badge } from "../../components/ui/Badge";
import { formatLatency } from "../../lib/limits";
import type { CallEventPayload } from "./types";

export interface CallEventCardProps {
  payload: CallEventPayload;
}

export function CallEventCard({ payload }: CallEventCardProps) {
  const failed = payload.status === "failed";
  return (
    <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
      <div style={{ display: "flex", gap: "var(--spacing-2)", flexWrap: "wrap" }}>
        <strong>{payload.modelDisplayName}</strong>
        <Badge
          label={failed ? "失败" : payload.status === "success" ? "成功" : payload.status}
          tone={failed ? "danger" : "success"}
        />
        <span style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}>
          {formatLatency(payload.latencyMs)}
        </span>
        {failed ? <span>重试 {payload.retryCount}</span> : null}
        {failed && payload.errorCode ? <span>{payload.errorCode}</span> : null}
      </div>
      <p style={{ margin: 0 }}>{payload.promptPreview}</p>
    </div>
  );
}
