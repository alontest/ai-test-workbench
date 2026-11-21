import { useEffect, useRef } from "react";
import { Button } from "../../../components/ui/Button";
import { Spinner } from "../../../components/ui/Loading";
import { isApiError } from "../../../lib/api/errors";
import { formatBytes, formatTimestamp } from "../format";
import { useRepoFile } from "../hooks/useRepoBrowse";
import styles from "./browse.module.css";

export interface FileTarget {
  repoId: string | null;
  ref: string;
  path: string;
}

export interface FileViewerDrawerProps {
  bindingId: string;
  open: boolean;
  target: FileTarget | null;
  disabled?: boolean;
  onClose: () => void;
}

function describeError(error: unknown): string {
  if (!isApiError(error)) {
    return "文件读取失败，请稍后重试。";
  }
  switch (error.code) {
    case "repo_file_too_large": {
      const detail = error.fieldError("sizeBytes");
      return detail
        ? `文件超过 1 MiB 上限，已拒绝读取（未截断）。${detail}`
        : "文件超过 1 MiB 上限，已拒绝读取（未截断）。";
    }
    case "repo_file_binary":
      return "该文件是二进制内容（base64 或含 NUL），不能按文本查看。";
    case "repo_file_not_utf8":
      return "文件不是合法的 UTF-8 文本，无法展示。";
    case "invalid_path":
      return "文件路径不合法，已在请求前拒绝，未产生读取记录。";
    case "invalid_ref":
      return "分支或 ref 不合法，已在请求前拒绝。";
    case "binding_revoked":
      return "绑定已解绑，文件读取不可用。";
    case "binding_not_found":
      return "仓库绑定不存在。";
    default:
      return error.message || "文件读取失败，请稍后重试。";
  }
}

export function FileViewerDrawer({
  bindingId,
  open,
  target,
  disabled,
  onClose,
}: FileViewerDrawerProps) {
  const drawerRef = useRef<HTMLElement>(null);
  const restoreRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const query = useRepoFile(
    bindingId,
    target?.repoId ?? null,
    target?.ref ?? null,
    target?.path ?? null,
    open && !disabled,
  );

  useEffect(() => {
    if (!open) {
      return;
    }
    restoreRef.current =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    drawerRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      restoreRef.current?.focus();
    };
  }, [open]);

  if (!open || !target) {
    return null;
  }

  return (
    <div className={styles.drawerOverlay} onMouseDown={onClose}>
      <aside
        ref={drawerRef}
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-label="文件查看"
        data-testid="file-drawer"
        tabIndex={-1}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className={styles.drawerHead}>
          <div className={styles.drawerTitle}>
            <span className={styles.mono}>{target.path}</span>
            <span className={styles.muted}>
              ref <span className={styles.mono}>{target.ref}</span>
              {query.data ? ` · ${formatBytes(query.data.sizeBytes)}` : ""}
              {query.data?.fetchedAt
                ? ` · 读取于 ${formatTimestamp(query.data.fetchedAt)}`
                : ""}
            </span>
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            aria-label="关闭文件查看"
          >
            关闭
          </Button>
        </div>
        <div className={styles.drawerBody}>
          {disabled ? (
            <p className={styles.readonlyNote}>
              已解绑：文件入口置灰，不发起任何供应商请求。
            </p>
          ) : query.isPending ? (
            <Spinner label="读取文件" />
          ) : query.isError ? (
            <div className={styles.fileError} role="alert" data-testid="file-error">
              <strong>无法查看该文件</strong>
              <p>{describeError(query.error)}</p>
            </div>
          ) : (
            <pre className={styles.fileContent} data-testid="file-content">
              {query.data?.content ?? ""}
            </pre>
          )}
        </div>
        <p className={styles.drawerFoot}>
          内容不写入会话制品与 AiCallRecord；若引用进分析，按 200,000 字符上限计入。
        </p>
      </aside>
    </div>
  );
}
