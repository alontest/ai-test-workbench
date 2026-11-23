import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import {
  getKnowledgeBase,
  listKnowledgeBases,
} from "../api/client";
import { kbKeys } from "../api/keys";

const KB_LIST_PAGE_SIZE = 50;

export function useKnowledgeBases(projectId?: number) {
  return useInfiniteQuery({
    queryKey: kbKeys.listScope(projectId),
    queryFn: ({ pageParam }) =>
      listKnowledgeBases({
        projectId,
        limit: KB_LIST_PAGE_SIZE,
        cursor: pageParam,
      }),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
  });
}

export function useKnowledgeBase(kbId: string | undefined) {
  return useQuery({
    queryKey: kbKeys.detail(kbId ?? ""),
    queryFn: () => getKnowledgeBase(kbId as string),
    enabled: Boolean(kbId),
  });
}
