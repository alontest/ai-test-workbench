import type {
  BranchSummary,
  CommitSummary,
  RepoBaselineDocument,
  RepoBindingSummary,
} from "./api/types";

const BINDING_ID = "6f1c9a0e5b7d4c2a8e3f1b0d9c7a6e54";

export function bindingFixture(
  overrides: Partial<RepoBindingSummary> = {},
): RepoBindingSummary {
  return {
    bindingId: BINDING_ID,
    projectId: 1,
    provider: "github",
    apiBaseUrl: "https://api.github.com",
    orgId: null,
    owner: "pay",
    repoId: "pay/checkout",
    repoName: "pay/checkout",
    displayName: "pay/checkout",
    defaultBranch: "main",
    tokenMasked: "ghp_****abcd",
    tokenExpiresAt: null,
    status: "connected",
    lastVerifiedAt: "2026-11-20T02:10:00Z",
    lastVerifyResult: "success",
    lastVerifyMessage: null,
    lastSyncAttemptAt: "2026-11-20T02:20:00Z",
    lastSyncStatus: "success",
    lastSyncSuccessAt: "2026-11-20T02:20:06Z",
    lastSyncDurationMs: 6200,
    lastSyncErrorCategory: null,
    lastSyncErrorMessage: null,
    lastSyncRetryAfter: null,
    baseline: {
      ref: "main",
      sha: "a1b2c3d",
      fetchedAt: "2026-11-20T02:20:06Z",
    },
    revokedAt: null,
    createdAt: "2026-11-19T08:00:00Z",
    updatedAt: "2026-11-20T02:20:06Z",
    ...overrides,
  };
}

export function branchFixture(
  overrides: Partial<BranchSummary> = {},
): BranchSummary {
  return {
    name: "main",
    isDefault: true,
    headSha: "a1b2c3d",
    committedAt: "2026-11-20T02:00:00Z",
    ...overrides,
  };
}

export function commitFixture(
  overrides: Partial<CommitSummary> = {},
): CommitSummary {
  return {
    sha: "a1b2c3d4e5f6a7b8",
    shortSha: "a1b2c3d",
    title: "fix(pay): 回调签名校验顺序调整",
    authorName: "lin.t",
    committedAt: "2026-11-20T01:21:00Z",
    ...overrides,
  };
}

export function baselineFixture(
  overrides: Partial<RepoBaselineDocument> = {},
): RepoBaselineDocument {
  return {
    bindingId: BINDING_ID,
    provider: "github",
    repoName: "pay/checkout",
    status: "connected",
    revoked: false,
    metadataSynced: true,
    lastSyncSuccessAt: "2026-11-20T02:20:06Z",
    repo: {
      repoId: "pay/checkout",
      fullName: "pay/checkout",
      defaultBranch: "main",
    },
    branches: [branchFixture(), branchFixture({ name: "release/4.2", isDefault: false })],
    commits: [commitFixture()],
    fetchedAt: "2026-11-20T02:20:06Z",
    guide: null,
    ...overrides,
  };
}
