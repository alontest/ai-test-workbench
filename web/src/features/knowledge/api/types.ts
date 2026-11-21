export type EntryType =
  | "term"
  | "entity"
  | "state"
  | "rule"
  | "process"
  | "api"
  | "domain_event"
  | "other";

export type FreshnessState = "fresh" | "stale" | "unknown";

export type InvalidReason = "kb_deleted" | "entry_not_found" | "superseded";

export type KnowledgeBaseStatus = "ready" | "superseded";

export const ENTRY_TYPE_LABELS: Record<EntryType, string> = {
  term: "术语",
  entity: "实体",
  state: "状态",
  rule: "业务规则",
  process: "流程",
  api: "接口",
  domain_event: "领域事件",
  other: "其他",
};

export const ENTRY_TYPES: EntryType[] = [
  "term",
  "entity",
  "state",
  "rule",
  "process",
  "api",
  "domain_event",
  "other",
];

export const INVALID_REASON_LABELS: Record<InvalidReason, string> = {
  kb_deleted: "知识库已删除",
  entry_not_found: "条目不存在",
  superseded: "已被新版本取代",
};

export interface ProjectRef {
  id: number | null;
  name: string | null;
}

export interface KnowledgeBaseVersion {
  kbId: string;
  name: string;
  version: number;
  current: boolean;
  status: KnowledgeBaseStatus;
  generatedAt: string | null;
  entryCount: number;
  fileCount: number;
  createdAt: string;
}

export interface KnowledgeBaseSummary extends KnowledgeBaseVersion {
  projectId: number;
  totalByteSize: number;
  supersededCount: number;
  latestKbId: string;
  project?: ProjectRef;
}

export interface KbVersionItem {
  kbId: string;
  version: number;
  current: boolean;
  status: KnowledgeBaseStatus;
  generatedAt: string | null;
  entryCount: number;
  fileCount: number;
  createdAt: string;
}

export interface ImportFileReport {
  name: string;
  size: number;
  accepted: boolean;
}

export interface SkippedEntry {
  index: number;
  line: number | null;
  code: string | null;
  reason: string;
}

export interface DuplicateBody {
  code: string;
  fileName: string;
}

export interface ImportCounts {
  files?: number;
  bytes?: number;
  entries?: number;
  skipped?: number;
}

export interface ImportMeta {
  fingerprint?: string;
  graphFingerprint?: string | null;
  warnings?: number;
}

export interface ImportReport {
  files?: ImportFileReport[];
  skippedEntries?: SkippedEntry[];
  unmatchedFiles?: string[];
  duplicateBodies?: DuplicateBody[];
  counts?: ImportCounts;
  versionBumped?: boolean;
  previousVersion?: number | null;
  meta?: ImportMeta;
}

export interface KnowledgeImportResponse {
  kb: KnowledgeBaseSummary;
  importReport: ImportReport;
}

export interface KnowledgeBaseDetail {
  kb: KnowledgeBaseVersion;
  project: ProjectRef;
  versions: KbVersionItem[];
  importReport: ImportReport;
  latestKbId: string;
  supersededBy: { kbId: string; version: number } | null;
}

export interface KbVersionList {
  items: KbVersionItem[];
  latestKbId: string;
  nextCursor: string | null;
}

export interface CountsByType {
  term: number;
  entity: number;
  state: number;
  rule: number;
  process: number;
  api: number;
  domain_event: number;
  other: number;
}

export interface Freshness {
  at: string | null;
  state: FreshnessState;
}

export interface EntryListItem {
  entryId: string;
  code: string;
  title: string;
  type: EntryType;
  kbId: string;
  kbName: string;
  kbVersion: number;
  superseded: boolean;
  bodyMissing: boolean;
  freshness: Freshness;
  conflict: { hasConflict: boolean };
}

export interface EntryPage {
  items: EntryListItem[];
  countsByType: CountsByType;
  total: number;
  nextCursor: string | null;
}

export interface EntryDetailKb {
  kbId: string;
  name: string;
  version: number;
  generatedAt: string | null;
  current: boolean;
  superseded: boolean;
  latestKbId: string;
}

export interface EntryNeighbor {
  code: string;
  title?: string;
  entryId?: string;
  kbId?: string;
  exists: boolean;
}

export interface ConflictSource {
  kbName: string;
  version: number;
  generatedAt: string | null;
}

export interface KnowledgeEntryDetail {
  entryId: string;
  code: string;
  title: string;
  type: EntryType;
  kb: EntryDetailKb;
  summary: string | null;
  body: string | null;
  bodyMissing: boolean;
  bodySourceFile: string | null;
  sourceDoc: string | null;
  anchor: string | null;
  fields: Record<string, unknown>;
  tables: string[];
  codePaths: string[];
  neighbors: EntryNeighbor[];
  freshness: Freshness;
  conflicts: ConflictSource[];
  createdAt: string;
}

export interface KnowledgeBasePage {
  items: KnowledgeBaseSummary[];
  nextCursor: string | null;
}

export interface KbEntryRef {
  kbId: string;
  code: string;
}

export interface KnowledgeRefBody {
  kbId: string;
  entryCodes: string[];
}

export interface InvalidItem {
  kbId: string;
  code: string;
  reason: InvalidReason;
}

export interface CandidatePage {
  projectId: number;
  items: EntryListItem[];
  countsByType: CountsByType;
  total: number;
  nextCursor: string | null;
}

export interface InjectionPreviewItem {
  kbId: string;
  kbName: string;
  kbVersion: number;
  code: string;
  title: string;
  chars: number;
  source: "body" | "summary";
}

export interface InjectionWarning {
  kind: "stale" | "conflict";
  kbId: string;
  code: string;
  detail: string;
}

export interface InjectionPreview {
  items: InjectionPreviewItem[];
  invalidItems: InvalidItem[];
  promptChars: number;
  injectedChars: number;
  totalChars: number;
  limit: number;
  overLimit: boolean;
  warnings: InjectionWarning[];
}
