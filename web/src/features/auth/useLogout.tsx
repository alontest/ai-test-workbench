import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { apiFetch } from "../../lib/api/client";

export function useLogout() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<void>("/auth/logout", {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.clear();
      navigate("/login?reason=logged-out", { replace: true });
    },
  });
}
