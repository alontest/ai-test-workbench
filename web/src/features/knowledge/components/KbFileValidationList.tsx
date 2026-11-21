import { Button } from "../../../components/ui/Button";
import { fileExtension, formatBytes } from "../../../lib/limits";
import styles from "./knowledge.module.css";

export const KB_ALLOWED_EXTENSIONS = [".json", ".md", ".markdown"] as const;
export const KB_MAX_FILES = 50;
export const KB_INDEX_MAX_BYTES = 20 * 1024 * 1024;
export const KB_FILE_MAX_BYTES = 10 * 1024 * 1024;
export const KB_MAX_TOTAL_BYTES = 100 * 1024 * 1024;

export interface FileValidation {
  name: string;
  size: number;
  error?: string;
}

export interface SelectionValidation {
  items: FileValidation[];
  problems: string[];
  canSubmit: boolean;
}

function isIndexFile(name: string): boolean {
  return name.toLowerCase() === "index.json";
}

/**
 * 前端只做扩展名 / 单文件大小 / 数量 / 合计的即时提示，
 * 不解析 index.json 结构——结构错误由服务端返回。
 */
export function validateKnowledgeFiles(files: File[]): SelectionValidation {
  const items = files.map<FileValidation>((file) => {
    const extension = fileExtension(file.name);
    if (!(KB_ALLOWED_EXTENSIONS as readonly string[]).includes(extension)) {
      return {
        name: file.name,
        size: file.size,
        error: `不支持 ${extension || "(无扩展名)"}；允许 .json / .md / .markdown`,
      };
    }
    if (isIndexFile(file.name) && file.size > KB_INDEX_MAX_BYTES) {
      return {
        name: file.name,
        size: file.size,
        error: `index.json 超过 20MB 上限（当前 ${formatBytes(file.size)}）`,
      };
    }
    if (!isIndexFile(file.name) && file.size > KB_FILE_MAX_BYTES) {
      return {
        name: file.name,
        size: file.size,
        error: `单文件超过 10MB 上限（当前 ${formatBytes(file.size)}）`,
      };
    }
    return { name: file.name, size: file.size };
  });

  const problems: string[] = [];
  if (files.length > KB_MAX_FILES) {
    problems.push(
      `单次最多 ${KB_MAX_FILES} 个文件，当前 ${files.length} 个`,
    );
  }
  if (!files.some((file) => isIndexFile(file.name))) {
    problems.push("必须包含 index.json");
  }
  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  if (totalBytes > KB_MAX_TOTAL_BYTES) {
    problems.push(
      `合计超过 100MB 上限（当前 ${formatBytes(totalBytes)}）`,
    );
  }

  const canSubmit =
    files.length > 0 &&
    problems.length === 0 &&
    items.every((item) => !item.error);
  return { items, problems, canSubmit };
}

export interface KbFileValidationListProps {
  files: File[];
  validation: SelectionValidation;
  onRemove: (index: number) => void;
}

export function KbFileValidationList({
  files,
  validation,
  onRemove,
}: KbFileValidationListProps) {
  if (files.length === 0) {
    return <p className={styles.muted}>请选择至少包含 index.json 的文件。</p>;
  }
  return (
    <div className={styles.stack}>
      <ul className={styles.fileList}>
        {validation.items.map((item, index) => (
          <li key={`${item.name}-${index}`} className={styles.fileRow}>
            <span className={styles.fileName}>{item.name}</span>
            <span className={item.error ? styles.fileError : styles.muted}>
              {item.error ?? formatBytes(item.size)}
            </span>
            <Button type="button" variant="ghost" onClick={() => onRemove(index)}>
              移除
            </Button>
          </li>
        ))}
      </ul>
      {validation.problems.length > 0 ? (
        <ul className={styles.reasonList} role="alert">
          {validation.problems.map((problem) => (
            <li key={problem} className={styles.fileError}>
              {problem}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
