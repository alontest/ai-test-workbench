import type { TreeEntry } from "../api/types";
import { formatBytes } from "../format";
import styles from "./browse.module.css";

export interface TreeNodeProps {
  entry: TreeEntry;
  depth: number;
  expanded: boolean;
  loading?: boolean;
  disabled?: boolean;
  onToggle: () => void;
  onOpen: () => void;
}

export function TreeNode({
  entry,
  depth,
  expanded,
  loading,
  disabled,
  onToggle,
  onOpen,
}: TreeNodeProps) {
  const isDir = entry.type === "dir";
  return (
    <button
      type="button"
      className={styles.treeRow}
      style={{ paddingLeft: `calc(var(--spacing-5) * ${depth} + var(--spacing-2))` }}
      aria-disabled={disabled || undefined}
      aria-expanded={isDir ? expanded : undefined}
      data-testid="tree-row"
      onClick={() => {
        if (disabled) {
          return;
        }
        if (isDir) {
          onToggle();
        } else {
          onOpen();
        }
      }}
    >
      <span className={styles.treeCaret} aria-hidden="true">
        {isDir ? (loading ? "…" : expanded ? "▾" : "▸") : ""}
      </span>
      <span className={styles.treeType}>{isDir ? "DIR" : "FILE"}</span>
      <span className={styles.treeName}>
        {entry.name}
        {isDir ? "/" : ""}
      </span>
      <span className={styles.treeSize}>
        {isDir ? "目录" : formatBytes(entry.sizeBytes)}
      </span>
    </button>
  );
}
