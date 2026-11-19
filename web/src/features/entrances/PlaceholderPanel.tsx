import { Link } from "react-router";
import { StatusPill } from "../../components/ui/Badge";
import styles from "./entrances.module.css";
import { DOMAIN_LABEL, type Entrance } from "./types";

export interface PlaceholderPanelProps {
  entrance: Entrance;
}

export function PlaceholderPanel({ entrance }: PlaceholderPanelProps) {
  const domainLabel = DOMAIN_LABEL[entrance.domain] ?? entrance.domain;
  return (
    <article className={styles.placeholder}>
      <h1>{entrance.name}</h1>
      <StatusPill status={entrance.status} />
      <p className={styles.meta}>
        所属域：{domainLabel}（{entrance.domain}）
      </p>
      <p>{entrance.description}</p>
      <p className={styles.callout}>
        该入口将在所属域交付后自动启用，当前不会创建会话，也不会调用模型。
      </p>
      <div className={styles.actions}>
        <Link to="/">返回首页</Link>
        <Link to="/sessions">查看分析会话</Link>
      </div>
    </article>
  );
}
