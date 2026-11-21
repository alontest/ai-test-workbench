import { Mascot } from "../../../components/mascot/Mascot";
import type { ImportReport } from "../api/types";
import styles from "./knowledge.module.css";

export interface KbImportReportProps {
  report: ImportReport;
  kbName: string;
  /** 本次导入后的知识库版本，用于展示版本跃迁。 */
  version?: number;
  versionBumped: boolean;
  previousVersion?: number | null;
}

export function KbImportReport({
  report,
  kbName,
  version,
  versionBumped,
  previousVersion,
}: KbImportReportProps) {
  const counts = report.counts ?? {};
  const skipped = report.skippedEntries ?? [];
  const unmatched = report.unmatchedFiles ?? [];
  const duplicates = report.duplicateBodies ?? [];
  return (
    <section className={styles.card} aria-label="导入报告">
      <div className={styles.reportHero}>
        <Mascot size={56} state="success" />
        <div className={styles.reportHeroBody}>
          <div className={styles.sectionHead}>
            <h2 style={{ margin: 0 }}>导入报告</h2>
            <span className={styles.muted}>{kbName}</span>
          </div>
          {version !== undefined ? (
            <p className={styles.reportVersions}>
              {versionBumped && previousVersion
                ? `v${previousVersion} → v${version}`
                : `v${version}`}
            </p>
          ) : null}
          <p>
            已导入 {(counts.entries ?? 0).toLocaleString("zh-CN")} 条 · 跳过{" "}
            {(counts.skipped ?? skipped.length).toLocaleString("zh-CN")} 条 ·
            文件 {counts.files ?? 0} 个（
            {(counts.bytes ?? 0).toLocaleString("zh-CN")} 字节）
          </p>
        </div>
      </div>
      {versionBumped ? (
        <p className={styles.bannerWarn}>
          同名重新导入，已生成新版本
          {previousVersion ? `（上一版本 v${previousVersion}）` : ""}
          ，旧版本只读保留。
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
