import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { Provider } from "../providers/types";
import { ModelDialog } from "./ModelDialog";
import { ModelTable } from "./ModelTable";
import type { ModelBinding } from "./types";

interface PageResponse {
  items: ModelBinding[];
  nextCursor: string | null;
}

export function ModelsPage() {
  const params = useParams();
  const providerId = Number(params.id);
  const queryClient = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<ModelBinding | undefined>();
  const providerQuery = useQuery({
    queryKey: queryKeys.provider(providerId),
    queryFn: () => apiFetch<Provider>(`/providers/${providerId}`),
    enabled: Number.isFinite(providerId),
  });
  const query = useQuery({
    queryKey: queryKeys.providerModels(providerId),
    queryFn: () =>
      apiFetch<PageResponse>(`/providers/${providerId}/models`),
    enabled: Number.isFinite(providerId),
  });
  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      apiFetch(`/models/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    onMutate: async ({ id, enabled }) => {
      await queryClient.cancelQueries({
        queryKey: queryKeys.providerModels(providerId),
      });
      const previous = queryClient.getQueryData<PageResponse>(
        queryKeys.providerModels(providerId),
      );
      if (previous) {
        queryClient.setQueryData<PageResponse>(queryKeys.providerModels(providerId), {
          ...previous,
          items: previous.items.map((item) =>
            item.modelId === id ? { ...item, enabled } : item,
          ),
        });
      }
      return { previous };
    },
    onError: (_error, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(
          queryKeys.providerModels(providerId),
          context.previous,
        );
      }
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.providerModels(providerId),
      });
    },
  });

  if (query.isPending || providerQuery.isPending) {
    return <Spinner label="加载模型" />;
  }
  if (query.isError) {
    return <ErrorState message="无法加载模型" onRetry={() => void query.refetch()} />;
  }

  return (
    <section>
      <p>
        <Link to="/providers">返回提供商</Link>
      </p>
      <header style={{ display: "flex", justifyContent: "space-between" }}>
        <h1>{providerQuery.data?.name ?? "模型"} </h1>
        <Button type="button" onClick={() => setCreating(true)}>
          新建模型
        </Button>
      </header>
      <ModelTable
        models={query.data.items}
        onEdit={setEditing}
        onToggle={(model, enabled) => toggle.mutate({ id: model.modelId, enabled })}
      />
      {creating || editing ? (
        <ModelDialog
          open
          providerId={providerId}
          model={editing}
          onClose={() => {
            setCreating(false);
            setEditing(undefined);
          }}
          onSaved={() => {
            void queryClient.invalidateQueries({
              queryKey: queryKeys.providerModels(providerId),
            });
          }}
        />
      ) : null}
    </section>
  );
}
