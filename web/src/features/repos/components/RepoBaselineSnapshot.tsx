import type { RepoBaselineDocument } from "../api/types";
import { formatTimestamp } from "../format";
import styles from "./browse.module.css";
import { CommitRow } from "./CommitRow";

export interface RepoBaselineSnapshotProps {
  document: RepoBaselineDocument;
  title?: string;
}

/** 只读基线快照：解绑或令牌失效时仍可查看，不发任何供应商请求。 */
export function RepoBaselineSnapshot({
  document,
  title = "上次同步基线快照",
}: RepoBaselineSnapshotProps) {
  if (!document.metadataSynced) {
    return (
      <p className={styles.baseline} data-testid="baseline-snapshot">
        从未同步
      </p>
    );
  }
  return (
    <section className={styles.card} data-testid="baseline-snapshot">
      <div className={styles.sectionHead}>
        <h2 className={styles.cardTitle}>{title}</h2>
        <span className={styles.muted}>
          同步于 {formatTimestamp(document.lastSyncSuccessAt)}
        </span>
      </div>
      <div className={styles.rowMeta}>
        <span className={styles.mono}>
          {document.repo?.repoId ?? document.repoName}
        </span>
        <span className={styles.muted}>
          默认分支{" "}
          <span className={styles.mono}>
            {document.repo?.defaultBranch ?? "—"}
          </span>
        </span>
      </div>
      <div className={styles.baselineGrid}>
        <div>
          <h3 className={styles.subTitle}>分支（{document.branches.length}）</h3>
          <ul className={styles.chipList}>
            {document.branches.map((branch) => (
              <li key={branch.name} className={styles.chip}>
                <span className={styles.mono}>{branch.name}</span>
                {branch.isDefault ? "（默认）" : ""}
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className={styles.subTitle}>提交（{document.commits.length}）</h3>
          <div className={styles.commitList}>
            {document.commits.map((commit) => (
              <CommitRow key={commit.sha} commit={commit} />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
