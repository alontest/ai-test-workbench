import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { ProviderDialog } from "./ProviderDialog";
import { ProviderTable } from "./ProviderTable";
import type { Provider } from "./types";

interface PageResponse {
  items: Provider[];
  nextCursor: string | null;
}

export function ProvidersPage() {
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Provider | undefined>();
  const query = useQuery({
    queryKey: queryKeys.providers,
    queryFn: () => apiFetch<PageResponse>("/providers"),
  });
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      apiFetch(`/providers/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.providers });
      const previous = queryClient.getQueryData<PageResponse>(queryKeys.providers);
      if (previous) {
        queryClient.setQueryData<PageResponse>(queryKeys.providers, {
          ...previous,
          items: previous.items.map((item) =>
            item.providerId === id ? { ...item, enabled } : item,
          ),
        });
      }
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.providers, context.previous);
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.providers });
    },
  });

  if (query.isPending) {
    return <Spinner label="加载提供商" />;
  }
  if (query.isError) {
    return (
      <ErrorState message="无法加载提供商" onRetry={() => void query.refetch()} />
    );
  }

  return (
    <section>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>AI 提供商</h1>
        <Button type="button" onClick={() => setCreating(true)}>
          新建提供商
        </Button>
      </header>
      <ProviderTable
        providers={query.data.items}
        onEdit={setEditing}
        onToggle={(provider, enabled) =>
          toggle.mutate({ id: provider.providerId, enabled })
        }
      />
      {creating || editing ? (
        <ProviderDialog
          open
          provider={editing}
          onClose={() => {
            setCreating(false);
            setEditing(undefined);
          }}
          onSaved={() => {
            void queryClient.invalidateQueries({ queryKey: queryKeys.providers });
          }}
        />
      ) : null}
    </section>
  );
}
