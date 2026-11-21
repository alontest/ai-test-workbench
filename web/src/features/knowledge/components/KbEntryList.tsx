import type { ReactNode } from "react";
import { Link } from "react-router";
import { Badge } from "../../../components/ui/Badge";
import type { EntryListItem } from "../api/types";
import { ENTRY_TYPE_LABELS } from "../api/types";
import { KbFreshnessBadge } from "./KbFreshnessBadge";
import styles from "./knowledge.module.css";

export interface KbEntryListProps {
  items: EntryListItem[];
  selected?: string[];
  unavailableCodes?: string[];
  onToggle?: (entryId: string, item: EntryListItem) => void;
  onOpen?: (entryId: string, item: EntryListItem) => void;
  showLibrary?: boolean;
  emptyMessage?: string;
}

export function entryHref(item: EntryListItem): string {
  return `/knowledge-bases/${item.kbId}/entries/${encodeURIComponent(item.code)}`;
}

export function KbEntryList({
  items,
  selected = [],
  unavailableCodes = [],
  onToggle,
  onOpen,
  showLibrary = false,
  emptyMessage = "没有符合条件的条目",
}: KbEntryListProps) {
  if (items.length === 0) {
    return <p className={styles.muted}>{emptyMessage}</p>;
  }
  return (
    <ul className={styles.list}>
      {items.map((item) => {
        const unavailable = unavailableCodes.includes(item.code);
        const checked = selected.includes(item.entryId) && !unavailable;
        let title: ReactNode;
        if (onOpen) {
          title = (
            <button
              type="button"
              className={styles.link}
              onClick={() => onOpen(item.entryId, item)}
            >
              {item.title || item.code}
            </button>
          );
        } else if (!onToggle) {
          title = (
            <Link className={styles.title} to={entryHref(item)}>
              {item.title || item.code}
            </Link>
          );
        } else {
          title = <span className={styles.title}>{item.title || item.code}</span>;
        }
        return (
          <li key={item.entryId} className={styles.listRow}>
            {onToggle ? (
              <input
                type="checkbox"
                checked={checked}
                disabled={unavailable}
                aria-label={`选择 ${item.code}`}
                onChange={() => onToggle(item.entryId, item)}
              />
            ) : null}
            <div className={styles.listMain}>
              <span className={styles.code}>{item.code}</span>
              {title}
              <span className={styles.badges}>
                <Badge label={ENTRY_TYPE_LABELS[item.type]} />
                <KbFreshnessBadge
                  state={item.freshness.state}
                  at={item.freshness.at}
                />
                {item.superseded ? <Badge label="旧版本" /> : null}
                {item.bodyMissing ? (
                  <Badge label="正文缺失" tone="warning" />
                ) : null}
                {item.conflict.hasConflict ? (
                  <Badge label="版本冲突" tone="warning" />
                ) : null}
                {unavailable ? <Badge label="不可用" tone="danger" /> : null}
              </span>
            </div>
            {showLibrary ? (
              <span className={styles.muted}>
                {item.kbName} v{item.kbVersion}
              </span>
            ) : null}
          </li>
        );
      })}
    </ul>
  );
}
