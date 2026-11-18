export const PROMPT_MAX_CHARS = 200_000;
export const MAX_ARTIFACT_BYTES = 10 * 1024 * 1024;
export const MAX_FILES_PER_UPLOAD = 10;
export const CALL_TIMEOUT_MS = 300_000;
export const PREVIEW_MAX_BYTES = 262_144;

export const ALLOWED_ARTIFACT_EXTENSIONS = [
  ".txt",
  ".md",
  ".markdown",
  ".log",
  ".json",
  ".yaml",
  ".yml",
  ".csv",
  ".sql",
] as const;

export function countChars(text: string): number {
  return Array.from(text).length;
}

export function fileExtension(fileName: string): string {
  const base = fileName.replace(/\\/g, "/").split("/").pop() ?? fileName;
  const index = base.lastIndexOf(".");
  return index >= 0 ? base.slice(index).toLowerCase() : "";
}

export function nextRenamedName(
  fileName: string,
  existing: Iterable<string>,
): string {
  const taken = existing instanceof Set ? existing : new Set(existing);
  if (!taken.has(fileName)) {
    return fileName;
  }
  const index = fileName.lastIndexOf(".");
  const stem = index >= 0 ? fileName.slice(0, index) : fileName;
  const ext = index >= 0 ? fileName.slice(index) : "";
  for (let n = 1; n <= 100; n += 1) {
    const candidate = `${stem}-${n}${ext}`;
    if (!taken.has(candidate)) {
      return candidate;
    }
  }
  return `${stem}-100${ext}`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} 字节`;
  }
  return `${(bytes / 1024).toFixed(1)} KB`;
}

export function formatLatency(ms: number): string {
  if (ms >= 1000) {
    return `${(ms / 1000).toFixed(1)}s`;
  }
  return `${ms}ms`;
}
