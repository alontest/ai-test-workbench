import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { apiFetch } from "../../../lib/api/client";
import { isApiError } from "../../../lib/api/errors";
import { queryKeys } from "../../../lib/api/keys";
import type { KnowledgeImportResponse } from "../api/types";
import { validateKnowledgeFiles } from "../components/KbFileValidationList";
import { KbImportPanel } from "../components/KbImportPanel";
import { KbImportReport } from "../components/KbImportReport";
import { useImportKnowledge } from "../hooks/useImportKnowledge";
import styles from "../components/knowledge.module.css";

interface ProjectPage {
  items: { projectId: number; name: string }[];
  nextCursor: string | null;
}

export function KnowledgeImportPage() {
  const navigate = useNavigate();
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [result, setResult] = useState<KnowledgeImportResponse | null>(null);
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<ProjectPage>("/projects"),
  });
  const mutation = useImportKnowledge();
  const validation = validateKnowledgeFiles(files);

  function submit() {
    if (!projectId) {
      setSubmitError("请选择项目。");
      return;
    }
    if (!validation.canSubmit) {
      return;
    }
    setSubmitError(null);
    mutation.mutate(
      {
        projectId: Number(projectId),
        name: name.trim() || undefined,
        files,
      },
      {
        onSuccess: (data) => setResult(data),
        onError: (error) =>
          setSubmitError(
            isApiError(error)
              ? `${error.message}（${error.code}）`
              : "导入失败，请重试。",
          ),
      },
    );
  }

  function reset() {
    setResult(null);
    setFiles([]);
    setName("");
    setSubmitError(null);
  }

  return (
    <section className={styles.page}>
      <div className={styles.stack}>
        <Link to="/knowledge-bases">← 知识库</Link>
        <h1 style={{ margin: 0 }}>导入知识库</h1>
        <p className={styles.muted}>
          同名重新导入会生成新版本，旧版本只读保留。
        </p>
      </div>

      {result ? (
        <div className={styles.stack}>
          <KbImportReport
            report={result.importReport}
            kbName={result.kb.name}
            versionBumped={result.importReport.versionBumped ?? false}
            previousVersion={result.importReport.previousVersion ?? null}
          />
          <div className={styles.actions}>
            <Button type="button" variant="secondary" onClick={reset}>
              再导入一个
            </Button>
            <Button
              type="button"
              onClick={() => navigate(`/knowledge-bases/${result.kb.kbId}`)}
            >
              查看知识库
            </Button>
          </div>
        </div>
      ) : (
        <div className={styles.stack}>
          <label className={styles.stack}>
            <span>项目</span>
            <Select
              aria-label="项目"
              value={projectId}
              placeholder="请选择项目"
              options={(projectsQuery.data?.items ?? []).map((project) => ({
                value: String(project.projectId),
                label: project.name,
              }))}
              onChange={setProjectId}
            />
          </label>
          <KbImportPanel
            files={files}
            validation={validation}
            name={name}
            submitting={mutation.isPending}
            submitError={submitError}
            onNameChange={setName}
            onFilesChange={setFiles}
            onSubmit={submit}
            onCancel={() => setFiles([])}
          />
        </div>
      )}
    </section>
  );
}
