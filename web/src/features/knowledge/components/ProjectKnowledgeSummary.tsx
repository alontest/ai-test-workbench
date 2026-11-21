import { Link } from "react-router";
import { useKnowledgeBases } from "../hooks/useKnowledgeBases";
import { formatTimestamp } from "../format";
import styles from "./knowledge.module.css";

const MAX_SUMMARY_ITEMS = 3;

export function ProjectKnowledgeSummary() {
  const query = useKnowledgeBases();
  const items =
    query.data?.pages
      .flatMap((page) => page.items)
      .filter((item) => item.current) ?? [];
  const shown = items.slice(0, MAX_SUMMARY_ITEMS);

  return (
    <div data-testid="knowledge-summary" data-mount="knowledge-summary">
      <section className={styles.card} aria-label="关联知识库">
        <div className={styles.sectionHead}>
          <h2 style={{ margin: 0 }}>关联知识库</h2>
          <Link to="/knowledge-bases">查看全部</Link>
        </div>
        {query.isPending ? (
          <p className={styles.muted}>加载关联知识库…</p>
        ) : query.isError ? (
          <p className={styles.muted}>无法加载关联知识库。</p>
        ) : shown.length === 0 ? (
          <p className={styles.muted}>
            还没有关联知识库。<Link to="/knowledge-bases/import">去导入</Link>
          </p>
        ) : (
          <ul className={styles.summaryList}>
            {shown.map((item) => (
              <li key={item.kbId} className={styles.summaryRow}>
                <span>
                  <span className={styles.mono}>{item.name}</span> v{item.version} ·{" "}
                  {item.entryCount.toLocaleString("zh-CN")} 条 · 生成于{" "}
                  {formatTimestamp(item.generatedAt)}
                  {item.project?.name ? ` · ${item.project.name}` : ""}
                </span>
                <Link to={`/knowledge-bases/${item.kbId}`}>浏览</Link>
              </li>
            ))}
            {items.length > shown.length ? (
              <li className={styles.muted}>
                还有 {items.length - shown.length} 个（最多展示{" "}
                {MAX_SUMMARY_ITEMS} 个）
              </li>
            ) : null}
          </ul>
        )}
      </section>
    </div>
  );
}
