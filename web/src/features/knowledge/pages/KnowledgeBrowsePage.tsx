import { useNavigate, useParams, useSearchParams } from "react-router";
import { Button } from "../../../components/ui/Button";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import { ENTRY_TYPES, type EntryType } from "../api/types";
import { KbBrowseLayout } from "../components/KbBrowseLayout";
import { KbEntryList } from "../components/KbEntryList";
import { KbSearchBox } from "../components/KbSearchBox";
import { KbTypeTabs } from "../components/KbTypeTabs";
import { useKnowledgeBase } from "../hooks/useKnowledgeBases";
import { useKnowledgeEntries } from "../hooks/useKnowledgeEntries";
import styles from "../components/knowledge.module.css";

function parseType(raw: string | null): EntryType | null {
  return raw && (ENTRY_TYPES as string[]).includes(raw)
    ? (raw as EntryType)
    : null;
}

export function KnowledgeBrowsePage() {
  const navigate = useNavigate();
  const params = useParams();
  const kbId = params.kbId ?? "";
  const [searchParams, setSearchParams] = useSearchParams();
  const q = searchParams.get("q") ?? "";
  const type = parseType(searchParams.get("type"));

  const detailQuery = useKnowledgeBase(kbId || undefined);
  const entriesQuery = useKnowledgeEntries({
    kbId,
    type: type ?? undefined,
    q: q || undefined,
    enabled: Boolean(kbId),
  });

  function setParam(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams);
    if (value) {
      next.set(key, value);
    } else {
      next.delete(key);
    }
    setSearchParams(next, { replace: true });
  }

  if (!kbId) {
    return <ErrorState message="知识库不存在" retryable={false} />;
  }
  if (detailQuery.isPending) {
    return <Spinner label="加载知识库" />;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return (
      <ErrorState
        message="无法加载知识库"
        onRetry={() => void detailQuery.refetch()}
      />
    );
  }

  const detail = detailQuery.data;
  const items = entriesQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const counts = entriesQuery.data?.pages[0]?.countsByType;
  const total = entriesQuery.data?.pages[0]?.total ?? 0;

  return (
    <KbBrowseLayout
      title={detail.kb.name}
      version={detail.kb.version}
      generatedAt={detail.kb.generatedAt}
      superseded={detail.kb.status === "superseded"}
      currentKbId={detail.kb.kbId}
      latestKbId={detail.latestKbId}
      versions={detail.versions}
      onSelectVersion={(nextKbId) => {
        const query = searchParams.toString();
        navigate(`/knowledge-bases/${nextKbId}${query ? `?${query}` : ""}`);
      }}
      toolbar={
        <div className={styles.stack}>
          <div className={styles.toolbar}>
            <KbSearchBox
              value={q}
              onChange={(next) => setParam("q", next || null)}
            />
            <span className={styles.muted}>共 {total} 条</span>
          </div>
          <KbTypeTabs
            value={type}
            counts={counts}
            onChange={(next) => setParam("type", next)}
          />
        </div>
      }
    >
      {entriesQuery.isError ? (
        <ErrorState
          message="无法加载条目"
          onRetry={() => void entriesQuery.refetch()}
        />
      ) : entriesQuery.isPending ? (
        <Spinner label="加载条目" />
      ) : items.length === 0 ? (
        <EmptyState
          title="没有符合条件的条目"
          description="试试更换编号前缀、关键词或类型筛选。"
          action={
            <Button type="button" onClick={() => setSearchParams({}, { replace: true })}>
              清除筛选
            </Button>
          }
        />
      ) : (
        <KbEntryList items={items} showLibrary />
      )}
      {entriesQuery.hasNextPage ? (
        <div className={styles.actions}>
          <Button
            type="button"
            variant="secondary"
            loading={entriesQuery.isFetchingNextPage}
            onClick={() => void entriesQuery.fetchNextPage()}
          >
            加载更多
          </Button>
        </div>
      ) : null}
    </KbBrowseLayout>
  );
}
