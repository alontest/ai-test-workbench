import styles from "./ui.module.css";
export function Spinner({ label }: { label?: string }) {
  return (
    <div role="status" aria-live="polite">
      <div className={styles.spinner} />
      {label ? <span>{label}</span> : <span className="sr-only">加载中</span>}
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className={styles.skeleton} style={{ marginBottom: 8 }} />
      ))}
    </div>
  );
}
