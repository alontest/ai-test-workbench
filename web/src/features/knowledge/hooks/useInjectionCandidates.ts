import { useInfiniteQuery } from "@tanstack/react-query";
import { listInjectionCandidates } from "../api/client";
import { kbKeys } from "../api/keys";

export const CANDIDATE_PAGE_SIZE = 50;

export function useInjectionCandidates(
  sessionId: number,
  filters: { q?: string; type?: string; enabled?: boolean } = {},
) {
  const enabled = (filters.enabled ?? true) && sessionId > 0;
  return useInfiniteQuery({
    queryKey: kbKeys.candidates(sessionId, {
      q: filters.q,
      type: filters.type,
    }),
    queryFn: ({ pageParam }) =>
      listInjectionCandidates(sessionId, {
        q: filters.q,
        type: filters.type,
        limit: CANDIDATE_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled,
  });
}
