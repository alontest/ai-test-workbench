import { useInfiniteQuery } from "@tanstack/react-query";
import {
  listKnowledgeBaseEntries,
  listKnowledgeEntries,
  type KnowledgeEntryFilters,
} from "../api/client";
import { kbKeys } from "../api/keys";

export const KB_ENTRY_PAGE_SIZE = 50;

export function useKnowledgeEntries(filters: KnowledgeEntryFilters) {
  const { kbId, enabled = true, ...rest } = filters;
  return useInfiniteQuery({
    queryKey: kbKeys.entries(filters),
    queryFn: ({ pageParam }) =>
      kbId
        ? listKnowledgeBaseEntries(kbId, {
            ...rest,
            limit: KB_ENTRY_PAGE_SIZE,
            cursor: pageParam,
          })
        : listKnowledgeEntries({
            ...rest,
            limit: KB_ENTRY_PAGE_SIZE,
            cursor: pageParam,
          }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
    enabled,
  });
}
