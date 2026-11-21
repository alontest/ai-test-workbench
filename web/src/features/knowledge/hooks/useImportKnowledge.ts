import { useMutation, useQueryClient } from "@tanstack/react-query";
import { importKnowledgeBase, type ImportKnowledgeInput } from "../api/client";
import { kbKeys } from "../api/keys";

export function useImportKnowledge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ImportKnowledgeInput) => importKnowledgeBase(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: kbKeys.all });
    },
  });
}
