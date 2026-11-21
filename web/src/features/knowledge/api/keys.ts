import type { KnowledgeEntryFilters } from "./client";

interface EntryScope {
  projectId?: number;
  kbId?: string;
  type?: string | null;
  q?: string | null;
}

function entryScope(filters: EntryScope) {
  return {
    projectId: filters.projectId ?? null,
    kbId: filters.kbId ?? null,
    type: filters.type ?? null,
    q: filters.q ?? null,
  };
}

export const kbKeys = {
  all: ["kb"] as const,
  listPage: (projectId?: number, cursor?: string | null) =>
    ["kb", "list", { projectId: projectId ?? null, cursor: cursor ?? null }] as const,
  listScope: (projectId?: number) =>
    ["kb", "list", { projectId: projectId ?? null }] as const,
  detail: (kbId: string) => ["kb", kbId, "detail"] as const,
  versions: (kbId: string) => ["kb", kbId, "versions"] as const,
  entries: (filters: KnowledgeEntryFilters) =>
    ["kb", "entries", entryScope(filters)] as const,
  entry: (entryId: string) => ["kb", entryId] as const,
  candidates: (
    sessionId: number,
    filters: { q?: string | null; type?: string | null },
  ) =>
    [
      "kb",
      sessionId,
      "candidates",
      entryScope({ type: filters.type, q: filters.q }),
    ] as const,
  preview: (sessionId: number, refsKey: string, prompt: string) =>
    ["kb", sessionId, "preview", { refsKey, prompt }] as const,
};
