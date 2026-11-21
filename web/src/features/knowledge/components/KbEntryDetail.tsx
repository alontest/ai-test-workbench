import { Link } from "react-router";
import { Badge } from "../../../components/ui/Badge";
import type { KnowledgeEntryDetail } from "../api/types";
import { ENTRY_TYPE_LABELS } from "../api/types";
import { formatTimestamp } from "../format";
import { KbConflictNotice } from "./KbConflictNotice";
import { KbFreshnessBadge } from "./KbFreshnessBadge";
import styles from "./knowledge.module.css";

export interface KbEntryDetailProps {
  entry: KnowledgeEntryDetail;
}

export function KbEntryDetail({ entry }: KbEntryDetailProps) {
  const fields = Object.entries(entry.fields);
  return (
    <div className={styles.detailGrid}>
      <div className={styles.stack}>
        <header className={styles.stack}>
          <div className={styles.row}>
            <span className={`${styles.code} ${styles.mono}`}>{entry.code}</span>
            <Badge label={ENTRY_TYPE_LABELS[entry.type]} />
            <KbFreshnessBadge
              state={entry.freshness.state}
              at={entry.freshness.at}
            />
            {entry.kb.superseded ? <Badge label="旧版本" /> : null}
          </div>
          <h1 style={{ margin: 0 }}>{entry.title || entry.code}</h1>
        </header>

        {entry.kb.superseded ? (
          <p className={styles.banner}>
            当前条目属于旧版本，已被新版本取代。
            <Link to={`/knowledge-bases/${entry.kb.latestKbId}`}>
              查看最新版
            </Link>
          </p>
        ) : null}

        <section className={styles.card}>
          <h2 style={{ marginTop: 0 }}>摘要</h2>
          <p className={styles.bodyText}>{entry.summary ?? "—"}</p>
        </section>

        <section className={styles.card}>
          <h2 className={styles.bodyHeading} style={{ marginTop: 0 }}>
            正文
            {entry.bodyMissing ? (
              <Badge label="正文缺失" tone="warning" />
            ) : null}
          </h2>
          {entry.body ? (
            <div className={styles.bodyText}>{entry.body}</div>
          ) : (
            <p className={styles.bodyText}>{entry.summary ?? "—"}</p>
          )}
        </section>

        <section className={styles.card}>
          <h2 style={{ marginTop: 0 }}>结构化信息</h2>
          <dl className={styles.kv}>
            <dt>字段</dt>
            <dd>
              {fields.length === 0 ? (
                "—"
              ) : (
                fields.map(([key, value]) => (
                  <div key={key}>
                    <span className={styles.mono}>{key}</span>:{" "}
                    {String(value)}
                  </div>
                ))
              )}
            </dd>
            <dt>表</dt>
            <dd>{entry.tables.length === 0 ? "—" : entry.tables.join("、")}</dd>
            <dt>代码路径</dt>
            <dd>
              {entry.codePaths.length === 0 ? (
                "—"
              ) : (
                entry.codePaths.map((path) => (
                  <div key={path} className={styles.mono}>
                    {path}
                  </div>
                ))
              )}
            </dd>
          </dl>
        </section>

        <section className={styles.card}>
          <h2 style={{ marginTop: 0 }}>一跳邻居</h2>
          {entry.neighbors.length === 0 ? (
            <p className={styles.muted}>—</p>
          ) : (
            <ul className={styles.reasonList}>
              {entry.neighbors.map((neighbor) =>
                neighbor.exists && neighbor.kbId ? (
                  <li key={neighbor.code}>
                    <Link
                      to={`/knowledge-bases/${neighbor.kbId}/entries/${encodeURIComponent(neighbor.code)}`}
                    >
                      <span className={styles.mono}>{neighbor.code}</span>
                      {neighbor.title ? ` ${neighbor.title}` : ""}
                    </Link>
                  </li>
                ) : (
                  <li key={neighbor.code} className={styles.muted}>
                    <span className={styles.mono}>{neighbor.code}</span> 不可用
                  </li>
                ),
              )}
            </ul>
          )}
        </section>
      </div>

      <aside className={styles.stack}>
        <section className={styles.card}>
          <h2 style={{ marginTop: 0 }}>来源与版本</h2>
          <dl className={styles.kv}>
            <dt>知识库</dt>
            <dd>
              <Link to={`/knowledge-bases/${entry.kb.kbId}`}>
                {entry.kb.name}
              </Link>
            </dd>
            <dt>版本</dt>
            <dd>v{entry.kb.version}</dd>
            <dt>生成时间</dt>
            <dd>{formatTimestamp(entry.kb.generatedAt)}</dd>
            <dt>来源文件</dt>
            <dd className={styles.mono}>{entry.sourceDoc ?? "—"}</dd>
            <dt>锚点</dt>
            <dd className={styles.mono}>{entry.anchor ?? "—"}</dd>
            <dt>正文来源</dt>
            <dd className={styles.mono}>{entry.bodySourceFile ?? "—"}</dd>
          </dl>
        </section>
        <section className={styles.card}>
          <h2 style={{ marginTop: 0 }}>冲突</h2>
          <KbConflictNotice conflicts={entry.conflicts} />
          {entry.conflicts.length === 0 ? (
            <p className={styles.muted}>未发现同编号的不同摘要。</p>
          ) : null}
        </section>
      </aside>
    </div>
  );
}
