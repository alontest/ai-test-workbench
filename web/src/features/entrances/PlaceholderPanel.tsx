import { Link } from "react-router";
import { Mascot } from "../../components/mascot/Mascot";
import { DOMAIN_LABEL, type Entrance } from "./types";
import styles from "./entrances.module.css";

export interface PlaceholderPanelProps {
  entrance: Entrance;
}

export function PlaceholderPanel({ entrance }: PlaceholderPanelProps) {
  const domainLabel = DOMAIN_LABEL[entrance.domain] ?? entrance.domain;
  return (
    <article className={styles.briefing}>
      <div className={styles.briefingHead}>
        <Mascot size={72} state="sleeping" label="鸮鸮" />
        <div className={styles.briefingCopy}>
          <span className={styles.eyebrow}>探长简报</span>
          <strong>该入口仍在路线图上</strong>
          <p className={styles.meta}>
            所属域：{domainLabel}（{entrance.domain}）
          </p>
        </div>
      </div>
      <p className={styles.callout}>
        该入口将在所属域交付后自动启用，当前不会创建会话，也不会调用模型。
      </p>
      <div className={styles.roadmap}>
        <span className={styles.roadmapStep}>01 所属域交付</span>
        <span className={styles.roadmapStep}>02 入口自动启用</span>
        <span className={styles.roadmapStep}>03 在会话中发起调用</span>
      </div>
      <div className={styles.actions}>
        <Link to="/sessions" className={styles.jump}>
          前往分析会话
        </Link>
        <Link to="/providers" className={styles.jump}>
          管理 AI 提供商
        </Link>
      </div>
    </article>
  );
}
