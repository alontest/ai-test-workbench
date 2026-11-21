import { useState } from "react";
import { useNavigate, useParams } from "react-router";
import { ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import type { FileTarget } from "../components/FileViewerDrawer";
import { FileViewerDrawer } from "../components/FileViewerDrawer";
import { BranchPicker } from "../components/BranchPicker";
import { CommitList } from "../components/CommitList";
import { RepoBaselineSnapshot } from "../components/RepoBaselineSnapshot";
import { RepoBrowseHeader } from "../components/RepoBrowseHeader";
import { RepoEmptyUnsynced } from "../components/RepoEmptyUnsynced";
import { RepoPicker } from "../components/RepoPicker";
import { RepoTree } from "../components/RepoTree";
import { RevokedNotice } from "../components/RevokedNotice";
import { TokenInvalidBanner } from "../components/TokenInvalidBanner";
import styles from "../components/browse.module.css";
import {
  useBranches,
  useCommits,
  useRepoBaseline,
  useRepositories,
} from "../hooks/useRepoBrowse";
import { useRepoBinding, useSyncRepo } from "../hooks/useRepoBindings";
import { useQueryClient } from "@tanstack/react-query";
import { repoKeys } from "../api/keys";
import type { RepoBindingSummary } from "../api/types";

export function RepoBrowsePage() {
  const params = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projectId = Number(params.projectId);
  const bindingId = params.bindingId ?? "";

  const [repoChoice, setRepoChoice] = useState<string | null>(null);
  const [refChoice, setRefChoice] = useState<string | null>(null);
  const [target, setTarget] = useState<FileTarget | null>(null);

  const bindingQuery = useRepoBinding(bindingId || undefined);
  const baselineQuery = useRepoBaseline(bindingId || undefined);
  const binding = bindingQuery.data;
  const revoked = binding?.status === "revoked";

  const reposQuery = useRepositories(bindingId, "", {
    enabled: Boolean(binding) && !revoked,
  });
  const activeRepoId = repoChoice ?? binding?.repoId ?? null;
  const branchesQuery = useBranches(bindingId, activeRepoId, "", {
    enabled: Boolean(binding) && !revoked,
  });
  const branches =
    branchesQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const activeRef =
    refChoice ??
    binding?.defaultBranch ??
    branches.find((branch) => branch.isDefault)?.name ??
    null;

  const metadataSynced =
    reposQuery.data?.pages[0]?.metadataSynced ??
    baselineQuery.data?.metadataSynced ??
    true;

  const commitsQuery = useCommits(bindingId, activeRepoId, activeRef, {
    enabled: Boolean(binding) && !revoked && metadataSynced && Boolean(activeRef),
  });
  const commits =
    commitsQuery.data?.pages.flatMap((page) => page.items) ?? [];

  const sync = useSyncRepo(Number.isFinite(projectId) ? projectId : undefined);

  if (!bindingId || !Number.isFinite(projectId)) {
    return <ErrorState message="仓库绑定不存在" retryable={false} />;
  }
  if (bindingQuery.isPending) {
    return <Spinner label="加载仓库绑定" />;
  }
  if (bindingQuery.isError || !binding) {
    return (
      <ErrorState
        message="无法加载仓库绑定"
        onRetry={() => void bindingQuery.refetch()}
      />
    );
  }

  const refreshing =
    reposQuery.isFetching ||
    branchesQuery.isFetching ||
    commitsQuery.isFetching;

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: repoKeys.all });
  }

  function renderLiveView() {
    if (metadataSynced === false) {
      return (
        <RepoEmptyUnsynced
          variant="browse"
          syncing={sync.isPending}
          onSync={() => sync.mutate(bindingId)}
        />
      );
    }
    if (reposQuery.isError) {
      return (
        <div className={styles.stack}>
          <ErrorState
            message="实时列表加载失败；已展示上次同步基线，未改动已保存数据"
            onRetry={() => void reposQuery.refetch()}
          />
          {baselineQuery.data ? (
            <RepoBaselineSnapshot document={baselineQuery.data} />
          ) : null}
        </div>
      );
    }
    return (
      <>
        <div className={styles.selectors}>
          <RepoPicker
            bindingId={bindingId}
            value={activeRepoId}
            onChange={(next) => {
              setRepoChoice(next);
              setRefChoice(null);
            }}
          />
          <BranchPicker
            bindingId={bindingId}
            repoId={activeRepoId}
            value={activeRef}
            onChange={(next) => setRefChoice(next)}
          />
        </div>
        <div className={styles.browseGrid}>
          <section className={styles.card} aria-label="目录树">
            <div className={styles.sectionHead}>
              <h2 className={styles.cardTitle}>目录树</h2>
              <span className={styles.muted}>逐级实时读取</span>
            </div>
            <RepoTree
              bindingId={bindingId}
              repoId={activeRepoId}
              ref={activeRef}
              onOpenFile={(path) => {
                if (!activeRef) {
                  return;
                }
                setTarget({ repoId: activeRepoId, ref: activeRef, path });
              }}
            />
          </section>
          <section className={styles.card} aria-label="提交">
            <div className={styles.sectionHead}>
              <h2 className={styles.cardTitle}>提交</h2>
              <span className={styles.muted}>按时间倒序 · 实时分页</span>
            </div>
            <CommitList
              items={commits}
              loading={commitsQuery.isPending}
              error={commitsQuery.isError}
              hasMore={Boolean(commitsQuery.hasNextPage)}
              loadingMore={commitsQuery.isFetchingNextPage}
              onLoadMore={() => void commitsQuery.fetchNextPage()}
              onRetry={() => void commitsQuery.refetch()}
            />
          </section>
        </div>
      </>
    );
  }

  function renderRevokedView() {
    return (
      <>
        <RevokedNotice binding={binding as RepoBindingSummary} />
        <div className={styles.selectors}>
          <RepoPicker
            bindingId={bindingId}
            value={binding?.repoId ?? null}
            onChange={() => undefined}
            disabled
          />
          <BranchPicker
            bindingId={bindingId}
            repoId={binding?.repoId ?? null}
            value={binding?.defaultBranch ?? null}
            onChange={() => undefined}
            disabled
          />
        </div>
        <div className={styles.browseGrid}>
          <section className={styles.card} aria-label="目录树">
            <div className={styles.sectionHead}>
              <h2 className={styles.cardTitle}>目录树</h2>
            </div>
            <RepoTree
              bindingId={bindingId}
              repoId={binding?.repoId ?? null}
              ref={binding?.defaultBranch ?? null}
              disabled
              onOpenFile={() => undefined}
            />
          </section>
          {baselineQuery.data ? (
            <RepoBaselineSnapshot document={baselineQuery.data} />
          ) : null}
        </div>
      </>
    );
  }

  return (
    <section className={styles.page}>
      <RepoBrowseHeader
        binding={binding}
        onRefresh={refresh}
        refreshing={refreshing}
      />
      {binding.status === "token_invalid" ? (
        <TokenInvalidBanner
          bindings={[binding]}
          onRefill={() => navigate("/projects")}
          onViewBaseline={() => undefined}
        />
      ) : null}
      {revoked ? renderRevokedView() : renderLiveView()}
      <FileViewerDrawer
        bindingId={bindingId}
        open={target !== null}
        target={target}
        disabled={revoked}
        onClose={() => setTarget(null)}
      />
    </section>
  );
}
