import styles from "./browse.module.css";

export interface TreeTruncatedNoteProps {
  visible: boolean;
}

export function TreeTruncatedNote({ visible }: TreeTruncatedNoteProps) {
  if (!visible) {
    return null;
  }
  return (
    <p className={styles.treeNote} role="note" data-testid="tree-truncated">
      目录树不完整，请逐级浏览
    </p>
  );
}
