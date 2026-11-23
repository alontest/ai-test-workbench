import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  getRepoBaseline,
  listBranches,
  listCommits,
  listRepositories,
  listTree,
  readRepoFile,
} from "../api/client";
import { repoKeys } from "../api/keys";

interface BrowseQueryOptions {
  enabled?: boolean;
}

const REPO_LIVE_PAGE_SIZE = 30;
const REPO_TREE_PAGE_SIZE = 100;

export function useRepositories(
  bindingId: string | undefined,
  search: string,
  options: BrowseQueryOptions = {},
) {
  const { enabled = true } = options;
  return useInfiniteQuery({
    queryKey: repoKeys.repositories(bindingId ?? "", search, null),
    queryFn: ({ pageParam }) =>
      listRepositories(bindingId as string, {
        search,
        limit: REPO_LIVE_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(bindingId) && enabled,
    staleTime: 0,
  });
}

export function useBranches(
  bindingId: string | undefined,
  repoId: string | null,
  search: string,
  options: BrowseQueryOptions = {},
) {
  const { enabled = true } = options;
  return useInfiniteQuery({
    queryKey: repoKeys.branches(bindingId ?? "", repoId, search, null),
    queryFn: ({ pageParam }) =>
      listBranches(bindingId as string, {
        repoId,
        search,
        limit: REPO_LIVE_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(bindingId) && enabled,
    staleTime: 0,
  });
}

export function useCommits(
  bindingId: string | undefined,
  repoId: string | null,
  ref: string | null,
  options: BrowseQueryOptions = {},
) {
  const { enabled = true } = options;
  return useInfiniteQuery({
    queryKey: repoKeys.commits(bindingId ?? "", repoId, ref, null),
    queryFn: ({ pageParam }) =>
      listCommits(bindingId as string, {
        repoId,
        ref: ref as string,
        limit: REPO_LIVE_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(bindingId) && Boolean(ref) && enabled,
    staleTime: 0,
  });
}

export function useRepoTree(
  bindingId: string | undefined,
  repoId: string | null,
  ref: string | null,
  path: string,
  options: BrowseQueryOptions = {},
) {
  const { enabled = true } = options;
  return useInfiniteQuery({
    queryKey: repoKeys.tree(bindingId ?? "", repoId, ref, path, null),
    queryFn: ({ pageParam }) =>
      listTree(bindingId as string, {
        repoId,
        ref: ref as string,
        path,
        limit: REPO_TREE_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(bindingId) && Boolean(ref) && enabled,
    staleTime: 0,
  });
}

export function useRepoFile(
  bindingId: string | undefined,
  repoId: string | null,
  ref: string | null,
  path: string | null,
  enabled: boolean,
) {
  return useQuery({
    queryKey: repoKeys.file(bindingId ?? "", repoId, ref, path ?? ""),
    queryFn: () =>
      readRepoFile(bindingId as string, {
        repoId,
        ref: ref as string,
        path: path as string,
      }),
    enabled:
      Boolean(bindingId) && Boolean(ref) && Boolean(path) && enabled,
    staleTime: 0,
    gcTime: 0,
  });
}

export function useRepoBaseline(bindingId: string | undefined) {
  return useQuery({
    queryKey: repoKeys.baseline(bindingId ?? ""),
    queryFn: () => getRepoBaseline(bindingId as string),
    enabled: Boolean(bindingId),
  });
}
