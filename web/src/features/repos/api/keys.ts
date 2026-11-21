export const repoKeys = {
  all: ["repo"] as const,
  bindings: (projectId: number) => ["repo", "bindings", projectId] as const,
  binding: (bindingId: string) => ["repo", "binding", bindingId] as const,
  syncRecords: (bindingId: string, cursor: string | null = null) =>
    ["repo", "sync-records", bindingId, cursor] as const,
  repositories: (bindingId: string, search: string, cursor: string | null) =>
    ["repo", "repositories", bindingId, { search, cursor }] as const,
  branches: (
    bindingId: string,
    repoId: string | null,
    search: string,
    cursor: string | null,
  ) =>
    ["repo", "branches", bindingId, { repoId, search, cursor }] as const,
  commits: (
    bindingId: string,
    repoId: string | null,
    ref: string | null,
    cursor: string | null,
  ) => ["repo", "commits", bindingId, { repoId, ref, cursor }] as const,
  tree: (
    bindingId: string,
    repoId: string | null,
    ref: string | null,
    path: string,
    cursor: string | null,
  ) => ["repo", "tree", bindingId, { repoId, ref, path, cursor }] as const,
  file: (
    bindingId: string,
    repoId: string | null,
    ref: string | null,
    path: string,
  ) => ["repo", "file", bindingId, repoId, ref, path] as const,
  baseline: (bindingId: string) => ["repo", "baseline", bindingId] as const,
};
