import type { ImportReport } from "../api/types";
import styles from "./knowledge.module.css";

export interface KbImportReportProps {
  report: ImportReport;
  kbName: string;
  versionBumped: boolean;
  previousVersion?: number | null;
}

export function KbImportReport({
  report,
  kbName,
  versionBumped,
  previousVersion,
}: KbImportReportProps) {
  const counts = report.counts ?? {};
  const skipped = report.skippedEntries ?? [];
  const unmatched = report.unmatchedFiles ?? [];
  const duplicates = report.duplicateBodies ?? [];
  return (
    <section className={styles.card} aria-label="导入报告">
      <div className={styles.sectionHead}>
        <h2 style={{ margin: 0 }}>导入报告</h2>
        <span className={styles.muted}>{kbName}</span>
      </div>
      <p>
        已导入 {(counts.entries ?? 0).toLocaleString("zh-CN")} 条 · 跳过{" "}
        {(counts.skipped ?? skipped.length).toLocaleString("zh-CN")} 条 · 文件{" "}
        {counts.files ?? 0} 个（{(counts.bytes ?? 0).toLocaleString("zh-CN")}{" "}
        字节）
      </p>
      {versionBumped ? (
        <p className={styles.banner}>
          同名重新导入，已生成新版本
          {previousVersion ? `（上一版本 v${previousVersion}）` : ""}，旧版本只读保留。
        </p>
      ) : null}
      {skipped.length > 0 ? (
        <div className={styles.stack}>
          <h3 style={{ margin: 0 }}>跳过的条目</h3>
          <ul className={styles.reasonList}>
            {skipped.map((item) => (
              <li key={`${item.index}-${item.code ?? ""}`}>
                第 {item.line ?? item.index} 行
                {item.code ? ` · ${item.code}` : ""} · {item.reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {unmatched.length > 0 ? (
        <div className={styles.stack}>
          <h3 style={{ margin: 0 }}>未匹配的文件</h3>
          <ul className={styles.reasonList}>
            {unmatched.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {duplicates.length > 0 ? (
        <div className={styles.stack}>
          <h3 style={{ margin: 0 }}>重复正文</h3>
          <ul className={styles.reasonList}>
            {duplicates.map((item) => (
              <li key={`${item.code}-${item.fileName}`}>
                {item.code} · {item.fileName}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
