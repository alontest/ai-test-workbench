import type { FreshnessState, InvalidReason } from "./api/types";
import { INVALID_REASON_LABELS } from "./api/types";

const UNKNOWN_TIME = "未知";

/** 统一按 UTC 展示，避免测试与不同时区机器出现漂移。 */
export function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return UNKNOWN_TIME;
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return UNKNOWN_TIME;
  }
  return `${parsed.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export const FRESHNESS_LABELS: Record<FreshnessState, string> = {
  fresh: "较新",
  stale: "可能过期",
  unknown: "未知",
};

export function invalidReasonLabel(reason: InvalidReason | string): string {
  return (
    INVALID_REASON_LABELS[reason as InvalidReason] ?? "未知原因"
  );
}

export function formatChars(value: number): string {
  return value.toLocaleString("zh-CN");
}
