import {
  ENTRY_TYPES,
  ENTRY_TYPE_LABELS,
  type CountsByType,
  type EntryType,
} from "../api/types";
import styles from "./knowledge.module.css";

export interface KbTypeTabsProps {
  value: EntryType | null;
  counts?: Partial<CountsByType>;
  onChange: (type: EntryType | null) => void;
}

export function KbTypeTabs({ value, counts, onChange }: KbTypeTabsProps) {
  const total = ENTRY_TYPES.reduce(
    (sum, type) => sum + (counts?.[type] ?? 0),
    0,
  );
  return (
    <div className={styles.tabs} role="tablist" aria-label="条目类型">
      <button
        type="button"
        role="tab"
        className={styles.tab}
        aria-selected={value === null}
        onClick={() => onChange(null)}
      >
        全部{counts ? ` ${total}` : ""}
      </button>
      {ENTRY_TYPES.map((type) => (
        <button
          key={type}
          type="button"
          role="tab"
          className={styles.tab}
          aria-selected={value === type}
          onClick={() => onChange(type)}
        >
          {ENTRY_TYPE_LABELS[type]}
          {counts ? ` ${counts[type] ?? 0}` : ""}
        </button>
      ))}
    </div>
  );
}
