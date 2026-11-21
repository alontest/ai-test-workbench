import { useState } from "react";
import { useNavigate } from "react-router";
import { Button } from "../../../components/ui/Button";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import type { RepoBindingSummary } from "../api/types";
import {
  useRepoBindings,
  useSyncRepo,
  useUnbindRepo,
} from "../hooks/useRepoBindings";
import { useTestRepoConnection } from "../hooks/useRepoConnectionTest";
import styles from "./repo.module.css";
import { RepoBindingForm } from "./RepoBindingForm";
import { RepoBindingList } from "./RepoBindingList";
import { TokenInvalidBanner } from "./TokenInvalidBanner";
import { UnbindDialog } from "./UnbindDialog";
import { UpdateTokenForm } from "./UpdateTokenForm";

export interface RepoBindingPanelProps {
  projectId: number | null;
}

export function RepoBindingPanel({ projectId }: RepoBindingPanelProps) {
  const navigate = useNavigate();
  const query = useRepoBindings(projectId ?? undefined);
  const test = useTestRepoConnection();
  const sync = useSyncRepo(projectId ?? undefined);
  const unbind = useUnbindRepo(projectId ?? undefined);

  const [form, setForm] = useState<{
    open: boolean;
    initial?: RepoBindingSummary;
  }>({ open: false });
  const [tokenBinding, setTokenBinding] = useState<RepoBindingSummary | null>(
    null,
  );
  const [unbindTarget, setUnbindTarget] = useState<RepoBindingSummary | null>(
    null,
  );

  const bindings = query.data?.pages.flatMap((page) => page.items) ?? [];
  const busy = test.isPending && test.variables?.bindingId
    ? { bindingId: test.variables.bindingId, kind: "testing" as const }
    : sync.isPending && sync.variables
      ? { bindingId: sync.variables, kind: "syncing" as const }
      : null;

  function goBrowse(bindingId: string) {
    if (projectId === null) {
      return;
    }
    navigate(`/projects/${projectId}/repos/${bindingId}`);
  }

  return (
    <div data-mount="repo-binding-panel" data-testid="repo-binding-panel">
      <section className={styles.card} aria-label="仓库绑定">
        <div className={styles.sectionHead}>
          <div>
            <h2 className={styles.cardTitle}>仓库绑定</h2>
            <p className={styles.muted}>
              只读取元数据与按需文件内容，不克隆仓库、不建立代码索引。
            </p>
          </div>
          <Button
            type="button"
            onClick={() => setForm({ open: true })}
            disabled={projectId === null}
          >
            + 添加绑定
          </Button>
        </div>
        <p className={styles.muted}>
          令牌只显示掩码；保存前可先用表单当前值测试，不落库、改字段即失效。
          绑定数量不设硬上限，建议不超过 5 个（控制同步耗时与限流风险）。
        </p>

        {projectId === null ? (
          <EmptyState
            title="先选择一个项目"
            description="选择左侧项目后，可在这里绑定仓库并测试连接。"
          />
        ) : (
          <>
            <TokenInvalidBanner
              bindings={bindings}
              onRefill={(bindingId) => {
                const target = bindings.find(
                  (binding) => binding.bindingId === bindingId,
                );
                setTokenBinding(target ?? null);
              }}
              onViewBaseline={goBrowse}
            />

            {query.isError ? (
              <ErrorState
                message="绑定列表加载失败，已绑定数据未受影响"
                onRetry={() => void query.refetch()}
              />
            ) : (
              <RepoBindingList
                bindings={bindings}
                loading={query.isPending}
                busy={busy}
                onTest={(bindingId) => test.mutate({ bindingId })}
                onSync={(bindingId) => sync.mutate(bindingId)}
                onBrowse={goBrowse}
                onUpdateToken={(binding) => setTokenBinding(binding)}
                onUnbind={setUnbindTarget}
                onRebind={(binding) => setForm({ open: true, initial: binding })}
              />
            )}

            {query.hasNextPage ? (
              <div className={styles.actionsInline}>
                <Button
                  type="button"
                  variant="secondary"
                  loading={query.isFetchingNextPage}
                  onClick={() => void query.fetchNextPage()}
                >
                  加载更多绑定
                </Button>
              </div>
            ) : null}

            {form.open ? (
              <RepoBindingForm
                projectId={projectId}
                open
                initial={form.initial}
                onClose={() => setForm({ open: false })}
                onSaved={() => setForm({ open: false })}
              />
            ) : null}
            {tokenBinding ? (
              <UpdateTokenForm
                binding={tokenBinding}
                open
                onClose={() => setTokenBinding(null)}
                onSaved={() => setTokenBinding(null)}
              />
            ) : null}

            <UnbindDialog
              open={unbindTarget !== null}
              binding={unbindTarget}
              loading={unbind.isPending}
              onCancel={() => setUnbindTarget(null)}
              onConfirm={() => {
                if (!unbindTarget) {
                  return;
                }
                unbind.mutate(unbindTarget.bindingId, {
                  onSettled: () => setUnbindTarget(null),
                });
              }}
            />
          </>
        )}
      </section>
    </div>
  );
}
