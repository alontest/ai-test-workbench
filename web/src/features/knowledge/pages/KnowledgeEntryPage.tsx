import { Link, useParams } from "react-router";
import { EmptyState, ErrorState } from "../../../components/ui/Feedback";
import { Spinner } from "../../../components/ui/Loading";
import { KbEntryDetail } from "../components/KbEntryDetail";
import { useEntryByCode, useEntryDetail } from "../hooks/useEntryDetail";
import styles from "../components/knowledge.module.css";

export function KnowledgeEntryPage() {
  const params = useParams();
  const kbId = params.kbId ?? "";
  const code = params.code ?? "";
  const matching = useEntryByCode(kbId || undefined, code || undefined);
  const detail = useEntryDetail(matching.data?.entryId);

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
  if (detail.isError || !detail.data) {
    return (
      <ErrorState
        message="无法加载条目详情"
        onRetry={() => void detail.refetch()}
      />
    );
  }

  return (
    <section className={styles.page}>
      <p>
        <Link to={`/knowledge-bases/${kbId}`}>← 知识库浏览</Link>
      </p>
      <KbEntryDetail entry={detail.data} />
    </section>
  );
}
