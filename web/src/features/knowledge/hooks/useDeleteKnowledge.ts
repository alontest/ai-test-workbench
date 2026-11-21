import { useMutation, useQueryClient } from "@tanstack/react-query";
import { deleteKnowledgeBase } from "../api/client";
import { kbKeys } from "../api/keys";

export function useDeleteKnowledge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (kbId: string) => deleteKnowledgeBase(kbId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: kbKeys.all });
    },
  });
}
