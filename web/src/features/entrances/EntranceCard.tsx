import { Link } from "react-router";
import { StatusPill } from "../../components/ui/Badge";
import styles from "./entrances.module.css";
import { DOMAIN_LABEL, type Entrance } from "./types";

export interface EntranceCardProps {
  entrance: Entrance;
}

export function EntranceCard({ entrance }: EntranceCardProps) {
  const domainLabel = DOMAIN_LABEL[entrance.domain] ?? entrance.domain;
  return (
    <Link to={`/entrances/${entrance.key}`} className={styles.card}>
      <h2>{entrance.name}</h2>
      <StatusPill status={entrance.status} />
      <p className={styles.meta}>{entrance.description}</p>
      <p className={styles.meta}>
        所属域：{domainLabel}（{entrance.domain}）
      </p>
    </Link>
  );
}
