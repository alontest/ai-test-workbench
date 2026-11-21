export const UNKNOWN_TIME = "未知";

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

export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) {
    return "—";
  }
  if (ms < 1000) {
    return `${ms}ms`;
  }
  return `${(ms / 1000).toFixed(1)}s`;
}

export function formatBytes(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined) {
    return "—";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function displayValue(value: string | null | undefined): string {
  return value && value.trim() ? value : "—";
}
