import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/Feedback";
import { Spinner } from "../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../components/ui/PageHeader";
import { apiFetch } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import { ProviderDialog } from "./ProviderDialog";
import { ProviderTable } from "./ProviderTable";
import styles from "./providers.module.css";
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

  return (
    <PageContainer tier="xl" className={styles.page}>
      <PageHeader
        title="AI 提供商"
        description="凭证只写不回显，列表仅展示掩码；连接测试使用表单当前值，不落库、改字段即失效。"
        actions={
          <Button type="button" onClick={() => setCreating(true)}>
            新建提供商
          </Button>
        }
      />
      {query.isPending ? (
        <div className={styles.tableCard}>
          <Spinner label="加载提供商" />
        </div>
      ) : query.isError ? (
        <div className={styles.tableCard}>
          <ErrorState
            message="无法加载提供商"
            onRetry={() => void query.refetch()}
          />
        </div>
      ) : (
        <ProviderTable
          providers={query.data.items}
          onEdit={setEditing}
          onToggle={(provider, enabled) =>
            toggle.mutate({ id: provider.providerId, enabled })
          }
        />
      )}
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
    </PageContainer>
  );
}
