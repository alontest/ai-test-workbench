import type { StatusChangePayload } from "./types";

export interface StatusChangeEventProps {
  payload: StatusChangePayload;
}

const STATUS_LABEL: Record<string, string> = {
  in_progress: "进行中",
  completed: "已完成",
  failed: "失败",
};

function statusLabel(status: string): string {
  return STATUS_LABEL[status] ?? status;
}

export function StatusChangeEvent({ payload }: StatusChangeEventProps) {
  return (
    <div style={{ display: "grid", gap: "var(--spacing-2)" }}>
      <strong>状态变更 · {statusLabel(payload.to)}</strong>
      <span style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}>
        原状态 {statusLabel(payload.from)} · {payload.actor}
        {payload.reason ? ` · ${payload.reason}` : ""}
      </span>
    </div>
  );
}
