import { Link, useParams } from "react-router";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import { PageContainer, PageHeader } from "../../../components/ui/PageHeader";
import { ENTRY_TYPE_LABELS } from "../api/types";
import { KbEntryDetail } from "../components/KbEntryDetail";
import { useEntryByCode, useEntryDetail } from "../hooks/useEntryDetail";
import { formatTimestamp } from "../format";
import styles from "../components/knowledge.module.css";

export function KnowledgeEntryPage() {
  const params = useParams();
  const kbId = params.kbId ?? "";
  const code = params.code ?? "";
  const matching = useEntryByCode(kbId || undefined, code || undefined);
  const detail = useEntryDetail(matching.data?.entryId);
  const entry = detail.data;

  function renderBody() {
    if (!kbId || !code) {
      return <ErrorState message="条目不存在" retryable={false} />;
    }
    if (matching.isPending) {
      return <Spinner label="加载条目" />;
    }
    if (matching.isError) {
      return (
        <ErrorState
          message="无法加载条目"
          onRetry={() => void matching.refetch()}
        />
      );
    }
    if (!matching.data) {
      return (
        <EmptyState
          title="条目不存在"
          description="该条目不存在，或已随知识库删除。"
          action={<Link to={`/knowledge-bases/${kbId}`}>返回浏览</Link>}
        />
      );
    }
    if (detail.isPending) {
      return <Spinner label="加载条目详情" />;
    }
    if (detail.isError || !entry) {
      return (
        <ErrorState
          message="无法加载条目详情"
          onRetry={() => void detail.refetch()}
        />
      );
    }
    return <KbEntryDetail entry={entry} />;
  }

  return (
    <PageContainer tier="md" className={styles.page}>
      <PageHeader
        backLink={{
          to: kbId ? `/knowledge-bases/${kbId}` : "/knowledge-bases",
          label: "知识库浏览",
        }}
        title={entry?.title || code || "条目详情"}
        badge={
          code ? <span className={styles.entryCodeBadge}>{code}</span> : undefined
        }
        description={
          entry
            ? `${ENTRY_TYPE_LABELS[entry.type]} · ${entry.kb.name} v${entry.kb.version} · 生成于 ${formatTimestamp(entry.kb.generatedAt)}`
            : "按编号查看知识条目的正文、结构化信息与一跳邻居。"
        }
      />
      {renderBody()}
    </PageContainer>
  );
}
