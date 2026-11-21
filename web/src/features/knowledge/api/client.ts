import { apiFetch, queryString } from "../../../lib/api/client";
import type { ApiError } from "../../../lib/api/errors";
import type {
  CandidatePage,
  EntryPage,
  InvalidItem,
  KbEntryRef,
  KnowledgeBaseDetail,
  KnowledgeBasePage,
  KnowledgeBaseSummary,
  KnowledgeEntryDetail,
  KnowledgeImportResponse,
  KnowledgeRefBody,
  KbVersionList,
  InjectionPreview,
} from "./types";

export interface KnowledgeEntryFilters {
  projectId?: number;
  kbId?: string;
  type?: string;
  q?: string;
  includeSuperseded?: boolean;
  limit?: number;
  cursor?: string | null;
  /** 仅前端使用：缺省 `true`。 */
  enabled?: boolean;
}

export interface KnowledgeBaseFilters {
  projectId?: number;
  includeSuperseded?: boolean;
  limit?: number;
  cursor?: string | null;
}

export function listKnowledgeBases(
  filters: KnowledgeBaseFilters = {},
): Promise<KnowledgeBasePage> {
  return apiFetch<KnowledgeBasePage>(
    `/knowledge-bases${queryString({
      projectId: filters.projectId,
      includeSuperseded: filters.includeSuperseded,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function getKnowledgeBase(kbId: string): Promise<KnowledgeBaseDetail> {
  return apiFetch<KnowledgeBaseDetail>(`/knowledge-bases/${kbId}`);
}

export function listKnowledgeBaseVersions(
  kbId: string,
): Promise<KbVersionList> {
  return apiFetch<KbVersionList>(`/knowledge-bases/${kbId}/versions`);
}

export function listKnowledgeEntries(
  filters: KnowledgeEntryFilters = {},
): Promise<EntryPage> {
  return apiFetch<EntryPage>(
    `/knowledge-entries${queryString({
      projectId: filters.projectId,
      kbId: filters.kbId,
      type: filters.type,
      q: filters.q,
      includeSuperseded: filters.includeSuperseded,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function listKnowledgeBaseEntries(
  kbId: string,
  filters: Omit<KnowledgeEntryFilters, "kbId" | "projectId"> = {},
): Promise<EntryPage> {
  return apiFetch<EntryPage>(
    `/knowledge-bases/${kbId}/entries${queryString({
      type: filters.type,
      q: filters.q,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function getKnowledgeEntry(entryId: string): Promise<KnowledgeEntryDetail> {
  return apiFetch<KnowledgeEntryDetail>(`/knowledge-entries/${entryId}`);
}

export interface ImportKnowledgeInput {
  projectId: number;
  name?: string;
  files: File[];
}

export function importKnowledgeBase(
  input: ImportKnowledgeInput,
): Promise<KnowledgeImportResponse> {
  const body = new FormData();
  body.append("projectId", String(input.projectId));
  if (input.name?.trim()) {
    body.append("name", input.name.trim());
  }
  for (const file of input.files) {
    body.append("files", file);
  }
  return apiFetch<KnowledgeImportResponse>("/knowledge-bases", {
    method: "POST",
    body,
  });
}

export function deleteKnowledgeBase(kbId: string): Promise<void> {
  return apiFetch<void>(`/knowledge-bases/${kbId}`, { method: "DELETE" });
}

export function listInjectionCandidates(
  sessionId: number,
  filters: { q?: string; type?: string; limit?: number; cursor?: string | null } = {},
): Promise<CandidatePage> {
  return apiFetch<CandidatePage>(
    `/sessions/${sessionId}/knowledge-injection/candidates${queryString({
      q: filters.q,
      type: filters.type,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function previewInjection(
  sessionId: number,
  input: { refs: KbEntryRef[]; userPrompt: string },
): Promise<InjectionPreview> {
  return apiFetch<InjectionPreview>(
    `/sessions/${sessionId}/knowledge-injection/preview`,
    {
      method: "POST",
      body: JSON.stringify({
        refs: input.refs.map(({ kbId, code }) => ({ kbId, code })),
        userPrompt: input.userPrompt,
      }),
    },
  );
}

/** 扁平选择按 `kbId` 分组为 core `/ai/complete` 的 `knowledgeRefs` 形状。 */
export function toKnowledgeRefs(refs: KbEntryRef[]): KnowledgeRefBody[] {
  const grouped = new Map<string, string[]>();
  for (const ref of refs) {
    const codes = grouped.get(ref.kbId);
    if (codes) {
      codes.push(ref.code);
    } else {
      grouped.set(ref.kbId, [ref.code]);
    }
  }
  return Array.from(grouped, ([kbId, entryCodes]) => ({ kbId, entryCodes }));
}

/** 稳定、可比较的选择键，用于 query key 与依赖数组。 */
export function refsKey(refs: KbEntryRef[]): string {
  return refs
    .map((ref) => `${ref.kbId}:${ref.code}`)
    .sort()
    .join("|");
}

export function sameRef(a: KbEntryRef, b: KbEntryRef): boolean {
  return a.kbId === b.kbId && a.code === b.code;
}

/**
 * `details` 在 core 错误体里可以是数组或对象；失效项固定放在
 * `details.invalidItems`。这里只读取标识，不信任其余字段。
 */
export function invalidItemsOf(error: ApiError): InvalidItem[] {
  const details = error.details as unknown;
  if (Array.isArray(details)) {
    return [];
  }
  const raw = (details as { invalidItems?: unknown } | null)?.invalidItems;
  if (!Array.isArray(raw)) {
    return [];
  }
  const items: InvalidItem[] = [];
  for (const item of raw) {
    if (typeof item !== "object" || item === null) {
      continue;
    }
    const record = item as Record<string, unknown>;
    if (
      typeof record.kbId === "string" &&
      typeof record.code === "string" &&
      (record.reason === "kb_deleted" ||
        record.reason === "entry_not_found" ||
        record.reason === "superseded")
    ) {
      items.push({
        kbId: record.kbId,
        code: record.code,
        reason: record.reason,
      });
    }
  }
  return items;
}

export type { KnowledgeBaseSummary };
