export type RepoProvider = "github" | "yunxiao";

export type RepoBindingStatus =
  | "unverified"
  | "connected"
  | "token_invalid"
  | "revoked";

export type RepoTestResult =
  | "success"
  | "auth-error"
  | "unreachable"
  | "permission-denied";

type SyncErrorCategory =
  | "auth"
  | "network"
  | "rate_limit"
  | "permission"
  | "other"
  | "interrupted";

export const PROVIDER_LABELS: Record<RepoProvider, string> = {
  yunxiao: "云效 Codeup",
  github: "GitHub",
};

export const DEFAULT_API_BASE_URL: Record<RepoProvider, string> = {
  yunxiao: "https://openapi-rdc.aliyuncs.com",
  github: "https://api.github.com",
};

export const REPO_BINDING_STATUS_LABELS: Record<RepoBindingStatus, string> = {
  unverified: "未验证",
  connected: "已连接",
  token_invalid: "令牌失效",
  revoked: "已解绑",
};

export const REPO_TEST_RESULT_LABELS: Record<RepoTestResult, string> = {
  success: "连接成功",
  "auth-error": "鉴权失败",
  unreachable: "网络不可达",
  "permission-denied": "权限不足",
};

export interface RepoBaseline {
  ref: string | null;
  sha: string | null;
  fetchedAt: string | null;
}

export interface RepoBindingSummary {
  bindingId: string;
  projectId: number;
  provider: RepoProvider;
  apiBaseUrl: string;
  orgId: string | null;
  owner: string | null;
  repoId: string;
  repoName: string;
  displayName: string;
  defaultBranch: string | null;
  tokenMasked: string;
  tokenExpiresAt: string | null;
  status: RepoBindingStatus;
  lastVerifiedAt: string | null;
  lastVerifyResult: RepoTestResult | null;
  lastVerifyMessage: string | null;
  lastSyncAttemptAt: string | null;
  lastSyncStatus: "success" | "failed" | null;
  lastSyncSuccessAt: string | null;
  lastSyncDurationMs: number | null;
  lastSyncErrorCategory: SyncErrorCategory | null;
  lastSyncErrorMessage: string | null;
  lastSyncRetryAfter: string | null;
  baseline: RepoBaseline | null;
  revokedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface RepoConnectionTestInput {
  provider: RepoProvider;
  repoIdentifier: string;
  orgId?: string | null;
  apiBaseUrl?: string | null;
  token: string;
}

export interface RepoBindingCreateInput extends RepoConnectionTestInput {}

export interface RepoConnectionTestResponse {
  result: RepoTestResult;
  testedAt: string;
  message: string;
  defaultBranch: string | null;
  latestCommitAt: string | null;
  retryAfterAt: string | null;
  bindingStatus: RepoBindingStatus | null;
}

export interface RepoSyncRecord {
  syncId: string;
  bindingId: string;
  startedAt: string;
  finishedAt: string | null;
  status: "success" | "failed" | "running";
  durationMs: number | null;
  repoCount: number | null;
  branchCount: number | null;
  commitCount: number | null;
  errorCategory: SyncErrorCategory | null;
  errorMessage: string | null;
  retryAfterAt: string | null;
}

interface RepoSyncBindingSummary {
  bindingId: string;
  status: RepoBindingStatus;
  lastSyncSuccessAt: string | null;
  baseline: RepoBaseline | null;
}

export interface RepoSyncResponse {
  record: RepoSyncRecord;
  binding: RepoSyncBindingSummary;
}

export interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export interface RepositorySummary {
  repoId: string;
  fullName: string;
  displayName: string;
  defaultBranch: string | null;
  webUrl: string | null;
}

export interface BranchSummary {
  name: string;
  isDefault: boolean;
  headSha: string | null;
  committedAt: string | null;
}

export interface CommitSummary {
  sha: string;
  shortSha: string | null;
  title: string | null;
  authorName: string | null;
  committedAt: string | null;
}

export interface TreeEntry {
  name: string;
  path: string;
  type: "file" | "dir";
  sizeBytes: number | null;
}

export interface BrowsePage<T> {
  metadataSynced: boolean;
  live: boolean;
  items: T[];
  nextCursor: string | null;
  total: number | null;
  guide: string | null;
}

export interface TreePage {
  metadataSynced: boolean;
  live: boolean;
  path: string;
  ref: string;
  items: TreeEntry[];
  truncated: boolean;
  hasMore: boolean;
  nextCursor: string | null;
  total: number | null;
  guide: string | null;
}

export interface RepoFileContent {
  path: string;
  ref: string;
  sizeBytes: number;
  encoding: "text";
  content: string;
  fetchedAt: string | null;
}

export interface RepoBaselineDocument {
  bindingId: string;
  provider: RepoProvider;
  repoName: string;
  status: RepoBindingStatus;
  revoked: boolean;
  metadataSynced: boolean;
  lastSyncSuccessAt: string | null;
  repo: {
    repoId: string | null;
    fullName: string | null;
    defaultBranch: string | null;
  } | null;
  branches: BranchSummary[];
  commits: CommitSummary[];
  fetchedAt: string | null;
  guide?: string | null;
}
