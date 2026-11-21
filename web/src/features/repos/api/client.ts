import { apiFetch, queryString } from "../../../lib/api/client";
import type {
  BranchSummary,
  BrowsePage,
  CommitSummary,
  Page,
  RepoBaselineDocument,
  RepoBindingCreateInput,
  RepoBindingSummary,
  RepoConnectionTestInput,
  RepoConnectionTestResponse,
  RepoFileContent,
  RepositorySummary,
  RepoSyncRecord,
  RepoSyncResponse,
  TreePage,
} from "./types";

export function listRepoBindings(
  projectId: number,
  filters: { limit?: number; cursor?: string | null } = {},
): Promise<Page<RepoBindingSummary>> {
  return apiFetch<Page<RepoBindingSummary>>(
    `/projects/${projectId}/repo-bindings${queryString({
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function createRepoBinding(
  projectId: number,
  input: RepoBindingCreateInput,
): Promise<RepoBindingSummary> {
  return apiFetch<RepoBindingSummary>(
    `/projects/${projectId}/repo-bindings`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function getRepoBinding(bindingId: string): Promise<RepoBindingSummary> {
  return apiFetch<RepoBindingSummary>(`/repo-bindings/${bindingId}`);
}

export function updateRepoToken(
  bindingId: string,
  token: string,
): Promise<RepoBindingSummary> {
  return apiFetch<RepoBindingSummary>(`/repo-bindings/${bindingId}/token`, {
    method: "PATCH",
    body: JSON.stringify({ token }),
  });
}

export function testSavedConnection(
  bindingId: string,
): Promise<RepoConnectionTestResponse> {
  return apiFetch<RepoConnectionTestResponse>(
    `/repo-bindings/${bindingId}/test-connection`,
    { method: "POST" },
  );
}

export function testUnsavedConnection(
  input: RepoConnectionTestInput,
): Promise<RepoConnectionTestResponse> {
  return apiFetch<RepoConnectionTestResponse>("/repo-bindings/test-connection", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function syncRepo(bindingId: string): Promise<RepoSyncResponse> {
  return apiFetch<RepoSyncResponse>(`/repo-bindings/${bindingId}/sync`, {
    method: "POST",
  });
}

export function listSyncRecords(
  bindingId: string,
  filters: { limit?: number; cursor?: string | null } = {},
): Promise<Page<RepoSyncRecord>> {
  return apiFetch<Page<RepoSyncRecord>>(
    `/repo-bindings/${bindingId}/sync-records${queryString({
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function unbindRepo(bindingId: string): Promise<RepoBindingSummary> {
  return apiFetch<RepoBindingSummary>(`/repo-bindings/${bindingId}/unbind`, {
    method: "POST",
  });
}

interface BrowseFilters {
  repoId?: string | null;
  search?: string;
  limit?: number;
  cursor?: string | null;
}

export function listRepositories(
  bindingId: string,
  filters: BrowseFilters = {},
): Promise<BrowsePage<RepositorySummary>> {
  return apiFetch<BrowsePage<RepositorySummary>>(
    `/repo-bindings/${bindingId}/repositories${queryString({
      search: filters.search,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function listBranches(
  bindingId: string,
  filters: BrowseFilters = {},
): Promise<BrowsePage<BranchSummary>> {
  return apiFetch<BrowsePage<BranchSummary>>(
    `/repo-bindings/${bindingId}/branches${queryString({
      repoId: filters.repoId,
      search: filters.search,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function listCommits(
  bindingId: string,
  filters: BrowseFilters & { ref: string },
): Promise<BrowsePage<CommitSummary>> {
  return apiFetch<BrowsePage<CommitSummary>>(
    `/repo-bindings/${bindingId}/commits${queryString({
      repoId: filters.repoId,
      ref: filters.ref,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function listTree(
  bindingId: string,
  filters: BrowseFilters & { ref: string; path?: string },
): Promise<TreePage> {
  return apiFetch<TreePage>(
    `/repo-bindings/${bindingId}/tree${queryString({
      repoId: filters.repoId,
      ref: filters.ref,
      path: filters.path,
      limit: filters.limit,
      cursor: filters.cursor,
    })}`,
  );
}

export function readRepoFile(
  bindingId: string,
  filters: { repoId?: string | null; ref: string; path: string },
): Promise<RepoFileContent> {
  return apiFetch<RepoFileContent>(
    `/repo-bindings/${bindingId}/file${queryString({
      repoId: filters.repoId,
      ref: filters.ref,
      path: filters.path,
    })}`,
  );
}

export function getRepoBaseline(
  bindingId: string,
): Promise<RepoBaselineDocument> {
  return apiFetch<RepoBaselineDocument>(`/repo-bindings/${bindingId}/baseline`);
}
