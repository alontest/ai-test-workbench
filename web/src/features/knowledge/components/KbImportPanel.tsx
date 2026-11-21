import { useState, type DragEvent } from "react";
import { Button } from "../../../components/ui/Button";
import { FormField } from "../../../components/ui/FormField";
import { Input } from "../../../components/ui/Input";
import {
  KbFileValidationList,
  type SelectionValidation,
} from "./KbFileValidationList";
import styles from "./knowledge.module.css";

export interface KbImportPanelProps {
  files: File[];
  validation: SelectionValidation;
  name: string;
  submitting: boolean;
  submitError?: string | null;
  onNameChange: (name: string) => void;
  onFilesChange: (files: File[]) => void;
  onSubmit: () => void;
  onCancel: () => void;
}

export function KbImportPanel({
  files,
  validation,
  name,
  submitting,
  submitError,
  onNameChange,
  onFilesChange,
  onSubmit,
  onCancel,
}: KbImportPanelProps) {
  const [dragging, setDragging] = useState(false);

  function addFiles(incoming: File[]) {
    if (incoming.length === 0) {
      return;
    }
    onFilesChange([...files, ...incoming]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    addFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <div className={styles.stack}>
      <div
        className={styles.dropzone}
        style={
          dragging
            ? {
                borderColor: "var(--color-accent)",
                borderStyle: "solid",
              }
            : undefined
        }
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <p style={{ margin: 0 }}>拖拽文件到这里，或点击选择（可多选）</p>
        <p className={styles.muted}>
          仅 .json / .md / .markdown；必须包含 index.json
        </p>
        <p className={styles.muted}>
          index.json ≤20MB · 其他单文件 ≤10MB · 单次 ≤50 个 · 单库合计 ≤100MB
        </p>
        <label>
          选择文件
          <input
            type="file"
            multiple
            accept=".json,.md,.markdown"
            aria-label="选择知识库文件"
            disabled={submitting}
            style={{ display: "block", margin: "var(--spacing-2) auto 0" }}
            onChange={(event) => {
              addFiles(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
          />
        </label>
      </div>

      <FormField label="知识库名称" hint="可选；缺省按服务端规则推导">
        <Input
          value={name}
          maxLength={200}
          disabled={submitting}
          onChange={(event) => onNameChange(event.target.value)}
        />
      </FormField>

      <KbFileValidationList
        files={files}
        validation={validation}
        onRemove={(index) =>
          onFilesChange(files.filter((_file, item) => item !== index))
        }
      />

      {submitError ? (
        <p className={styles.bannerError} role="alert">
          {submitError}
        </p>
      ) : null}

      <div className={styles.actions}>
        <Button
          type="button"
          variant="ghost"
          disabled={submitting || files.length === 0}
          onClick={onCancel}
        >
          取消
        </Button>
        <Button
          type="button"
          disabled={!validation.canSubmit || submitting}
          loading={submitting}
          onClick={onSubmit}
        >
          提交导入
        </Button>
      </div>
    </div>
  );
}
