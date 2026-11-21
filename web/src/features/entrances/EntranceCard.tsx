import type { ComponentType } from "react";
import { Link } from "react-router";
import {
  FeatureBugAnalysis,
  FeatureCaseLibrary,
  FeatureLogTriage,
  FeatureRegressionList,
  FeatureSession,
  FeatureSqlAnalysis,
  FeatureTestReport,
  type IconProps,
} from "../../components/icons";
import { StatusPill } from "../../components/ui/Badge";
import styles from "./entrances.module.css";
import { DOMAIN_LABEL, type Entrance } from "./types";

const ENTRANCE_ICONS: Record<string, ComponentType<IconProps>> = {
  "case-library": FeatureCaseLibrary,
  "bug-analysis": FeatureBugAnalysis,
  "log-triage": FeatureLogTriage,
  "sql-analysis": FeatureSqlAnalysis,
  "regression-list": FeatureRegressionList,
  "test-report": FeatureTestReport,
};

export interface EntranceCardProps {
  entrance: Entrance;
}

export function EntranceCard({ entrance }: EntranceCardProps) {
  const domainLabel = DOMAIN_LABEL[entrance.domain] ?? entrance.domain;
  const Icon = ENTRANCE_ICONS[entrance.key] ?? FeatureSession;
  return (
    <Link to={`/entrances/${entrance.key}`} className={styles.card}>
      <span className={styles.cardHead}>
        <span className={styles.cardIdentity}>
          <span className={styles.cardIcon} aria-hidden="true">
            <Icon size={24} />
          </span>
          <span className={styles.cardName}>{entrance.name}</span>
        </span>
        <StatusPill status={entrance.status} />
      </span>
      <span className={styles.cardBody}>{entrance.description}</span>
      <span className={styles.cardFoot}>
        {entrance.domain}
        <span className={styles.cardDomain}>{domainLabel}</span>
      </span>
    </Link>
  );
}
