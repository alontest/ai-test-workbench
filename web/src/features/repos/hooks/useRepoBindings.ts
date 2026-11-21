import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import {
  createRepoBinding,
  getRepoBinding,
  listRepoBindings,
  listSyncRecords,
  syncRepo,
  unbindRepo,
  updateRepoToken,
} from "../api/client";
import { repoKeys } from "../api/keys";
import type {
  RepoBindingCreateInput,
  RepoBindingSummary,
  RepoSyncResponse,
} from "../api/types";

export const REPO_BINDING_PAGE_SIZE = 30;
export const REPO_SYNC_RECORD_PAGE_SIZE = 20;

export function useRepoBindings(projectId?: number) {
  return useInfiniteQuery({
    queryKey: repoKeys.bindings(projectId ?? 0),
    queryFn: ({ pageParam }) =>
      listRepoBindings(projectId as number, {
        limit: REPO_BINDING_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: typeof projectId === "number" && Number.isFinite(projectId),
  });
}

export function useRepoBinding(bindingId: string | undefined) {
  return useQuery({
    queryKey: repoKeys.binding(bindingId ?? ""),
    queryFn: () => getRepoBinding(bindingId as string),
    enabled: Boolean(bindingId),
  });
}

export function useCreateRepoBinding(projectId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: RepoBindingCreateInput) =>
      createRepoBinding(projectId, input),
    onSuccess: (binding) => {
      queryClient.setQueryData(repoKeys.binding(binding.bindingId), binding);
      void queryClient.invalidateQueries({
        queryKey: repoKeys.bindings(projectId),
      });
    },
  });
}

export function useUpdateRepoToken(bindingId: string, projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (token: string) => updateRepoToken(bindingId, token),
    onSuccess: (binding) => {
      queryClient.setQueryData(repoKeys.binding(bindingId), binding);
      void queryClient.invalidateQueries({
        queryKey: repoKeys.binding(bindingId),
      });
      if (projectId !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: repoKeys.bindings(projectId),
        });
      }
    },
  });
}

export function useSyncRepo(projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation<RepoSyncResponse, Error, string>({
    mutationFn: (bindingId: string) => syncRepo(bindingId),
    onSuccess: (_result, bindingId) => {
      void queryClient.invalidateQueries({
        queryKey: repoKeys.binding(bindingId),
      });
      void queryClient.invalidateQueries({
        queryKey: ["repo", "sync-records", bindingId],
      });
      void queryClient.invalidateQueries({
        queryKey: repoKeys.baseline(bindingId),
      });
      for (const scope of ["repositories", "branches", "commits", "tree"]) {
        void queryClient.invalidateQueries({
          queryKey: ["repo", scope, bindingId],
        });
      }
      if (projectId !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: repoKeys.bindings(projectId),
        });
      }
    },
  });
}

export function useSyncRecords(bindingId: string | undefined, open: boolean) {
  return useInfiniteQuery({
    queryKey: repoKeys.syncRecords(bindingId ?? ""),
    queryFn: ({ pageParam }) =>
      listSyncRecords(bindingId as string, {
        limit: REPO_SYNC_RECORD_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled: Boolean(bindingId) && open,
  });
}

export function useUnbindRepo(projectId?: number) {
  const queryClient = useQueryClient();
  return useMutation<RepoBindingSummary, Error, string>({
    mutationFn: (bindingId: string) => unbindRepo(bindingId),
    onSuccess: (binding) => {
      queryClient.setQueryData(repoKeys.binding(binding.bindingId), binding);
      void queryClient.invalidateQueries({ queryKey: repoKeys.all });
      if (projectId !== undefined) {
        void queryClient.invalidateQueries({
          queryKey: repoKeys.bindings(projectId),
        });
      }
    },
  });
}
