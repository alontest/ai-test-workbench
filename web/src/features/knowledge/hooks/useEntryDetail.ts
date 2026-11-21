import { useQuery } from "@tanstack/react-query";
import {
  getKnowledgeEntry,
  listKnowledgeBaseEntries,
} from "../api/client";
import { kbKeys } from "../api/keys";
import type { EntryListItem } from "../api/types";

export function useEntryDetail(entryId: string | undefined) {
  return useQuery({
    queryKey: kbKeys.entry(entryId ?? ""),
    queryFn: () => getKnowledgeEntry(entryId as string),
    enabled: Boolean(entryId),
  });
}

/** 按 `kbId` + 编号解析条目；路由参数只有编号，没有 entryId。 */
export function useEntryByCode(
  kbId: string | undefined,
  code: string | undefined,
) {
  return useQuery<EntryListItem | null>({
    queryKey: [...kbKeys.entries({ kbId, q: code }), "code"],
    queryFn: async () => {
      const page = await listKnowledgeBaseEntries(kbId as string, {
        q: code,
        limit: 50,
      });
      const wanted = (code as string).toLowerCase();
      return (
        page.items.find((item) => item.code.toLowerCase() === wanted) ?? null
      );
    },
    enabled: Boolean(kbId && code),
  });
}
