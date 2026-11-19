import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { apiFetchBlob, apiFetchText } from "../../lib/api/client";
import { formatBytes } from "../../lib/limits";

export interface ArtifactCardProps {
  fileName: string;
  byteSize: number;
  error?: string;
  renameHint?: string;
  artifactId?: number;
  onRemove?: () => void;
}

export function ArtifactCard({
  fileName,
  byteSize,
  error,
  renameHint,
  artifactId,
  onRemove,
}: ArtifactCardProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onPreview() {
    if (artifactId === undefined) {
      return;
    }
    setLoading(true);
    try {
      const text = await apiFetchText(
        `/artifacts/${artifactId}/content?mode=inline`,
      );
      setPreview(text);
    } finally {
      setLoading(false);
    }
  }

  async function onDownload() {
    if (artifactId === undefined) {
      return;
    }
    const blob = await apiFetchBlob(
      `/artifacts/${artifactId}/content?mode=download`,
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName;
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      style={{
        border: `1px solid ${error ? "var(--color-destructive)" : "var(--color-border)"}`,
        borderRadius: "var(--radius-md)",
        padding: "var(--spacing-3)",
        background: "var(--color-card)",
        display: "grid",
        gap: "var(--spacing-2)",
      }}
    >
      <strong>{fileName}</strong>
      <span style={{ color: "var(--color-muted-foreground)", fontSize: "var(--font-size-sm)" }}>
        {formatBytes(byteSize)}
      </span>
      {renameHint ? (
        <p style={{ margin: 0, color: "var(--color-warning)" }}>{renameHint}</p>
      ) : null}
      {error ? (
        <p role="alert" style={{ margin: 0, color: "var(--color-destructive)" }}>
          {error}
        </p>
      ) : null}
      <div style={{ display: "flex", gap: "var(--spacing-2)" }}>
        {artifactId !== undefined ? (
          <>
            <Button
              type="button"
              variant="ghost"
              onClick={() => void onPreview()}
              loading={loading}
            >
              预览
            </Button>
            <Button type="button" variant="ghost" onClick={() => void onDownload()}>
              下载
            </Button>
          </>
        ) : null}
        {onRemove ? (
          <Button type="button" variant="ghost" onClick={onRemove}>
            移除
          </Button>
        ) : null}
      </div>
      {preview !== null ? (
        <pre
          style={{
            whiteSpace: "pre-wrap",
            fontFamily: "var(--font-family-mono)",
            fontSize: "var(--font-size-sm)",
            margin: 0,
          }}
        >
          {preview}
        </pre>
      ) : null}
    </div>
  );
}
