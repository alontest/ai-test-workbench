import { useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";

const LOGIN_FIELD = "password";

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (secret: string) =>
      apiFetch<{ authenticated: boolean }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ [LOGIN_FIELD]: secret }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.session });
    },
  });
}
