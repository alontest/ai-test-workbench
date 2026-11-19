import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type DragEvent } from "react";
import { Button } from "../../components/ui/Button";
import { apiFetch } from "../../lib/api/client";
import {
  ALLOWED_ARTIFACT_EXTENSIONS,
  fileExtension,
  MAX_ARTIFACT_BYTES,
  MAX_FILES_PER_UPLOAD,
  nextRenamedName,
} from "../../lib/limits";
import { ArtifactCard } from "./ArtifactCard";

export interface FileUploaderProps {
  sessionId: number;
  existingFileNames?: string[];
  readOnly?: boolean;
}

interface SelectedFile {
  id: string;
  file: File;
  error?: string;
  renameHint?: string;
}

let fileSeq = 0;

function validateFile(file: File): string | undefined {
  const ext = fileExtension(file.name);
  if (!(ALLOWED_ARTIFACT_EXTENSIONS as readonly string[]).includes(ext)) {
    return `不支持 ${ext || "(无扩展名)"}；允许 .txt .md .markdown .log .json .yaml .yml .csv .sql`;
  }
  if (file.size > MAX_ARTIFACT_BYTES) {
    return `${file.name} 超过 10MB 上限`;
  }
  return undefined;
}

function withHints(
  files: SelectedFile[],
  existingFileNames: string[],
): SelectedFile[] {
  const taken = new Set(existingFileNames);
  return files.map((item) => {
    const renamed = nextRenamedName(item.file.name, taken);
    taken.add(renamed);
    return {
      ...item,
      renameHint:
        renamed !== item.file.name ? `将自动改名为 ${renamed}` : undefined,
    };
  });
}

export function FileUploader({
  sessionId,
  existingFileNames = [],
  readOnly = false,
}: FileUploaderProps) {
  const queryClient = useQueryClient();
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const mutation = useMutation({
    mutationFn: async (payload: File[]) => {
      const body = new FormData();
      for (const file of payload) {
        body.append("files", file);
      }
      return apiFetch(`/sessions/${sessionId}/artifacts`, {
        method: "POST",
        body,
      });
    },
    onSuccess: async () => {
      setFiles([]);
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
    },
  });

  const tooMany = files.length > MAX_FILES_PER_UPLOAD;
  const hinted = withHints(files, existingFileNames);
  const hasError = tooMany || hinted.some((item) => item.error);
  const canUpload =
    !readOnly && hinted.length > 0 && !hasError && !mutation.isPending;

  function addFiles(list: File[]) {
    setFiles((prev) => [
      ...prev,
      ...list.map((file) => ({
        id: `${file.name}-${(fileSeq += 1)}`,
        file,
        error: validateFile(file),
      })),
    ]);
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    if (readOnly) {
      return;
    }
    addFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <div style={{ display: "grid", gap: "var(--spacing-3)" }}>
      <div
        onDragOver={(event) => {
          event.preventDefault();
          if (!readOnly) {
            setDragging(true);
          }
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{
          border: "1px dashed var(--color-border)",
          borderColor: dragging ? "var(--color-accent)" : "var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "var(--spacing-6)",
          textAlign: "center",
          background: "var(--color-muted)",
        }}
      >
        <label>
          选择文件
          <input
            type="file"
            multiple
            disabled={readOnly}
            style={{ display: "block", margin: "var(--spacing-2) auto 0" }}
            onChange={(event) => {
              addFiles(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
          />
        </label>
        <p style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}>
          或拖拽到此处，单次最多 10 个，单文件上限 10MB
        </p>
      </div>
      {tooMany ? (
        <p role="alert" style={{ color: "var(--color-destructive)", margin: 0 }}>
          单次最多上传 10 个文件
        </p>
      ) : null}
      {hinted.map((item) => (
        <ArtifactCard
          key={item.id}
          fileName={item.file.name}
          byteSize={item.file.size}
          error={item.error}
          renameHint={item.renameHint}
          onRemove={
            readOnly
              ? undefined
              : () =>
                  setFiles((prev) => prev.filter((entry) => entry.id !== item.id))
          }
        />
      ))}
      <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
        {files.length > 0 ? (
          <Button
            type="button"
            variant="ghost"
            disabled={readOnly}
            onClick={() => setFiles([])}
          >
            清空
          </Button>
        ) : null}
        <Button
          type="button"
          disabled={!canUpload}
          loading={mutation.isPending}
          onClick={() =>
            mutation.mutate(hinted.filter((item) => !item.error).map((item) => item.file))
          }
        >
          上传
        </Button>
      </div>
    </div>
  );
}
