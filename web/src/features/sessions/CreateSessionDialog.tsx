import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { Button } from "../../components/ui/Button";
import { FormField } from "../../components/ui/FormField";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { apiFetch, queryString } from "../../lib/api/client";
import { queryKeys } from "../../lib/api/keys";
import type { Project } from "../projects/types";
import type { EnabledModel } from "./types";

const ENTRANCES = [
  { value: "case-library", label: "用例库" },
  { value: "regression-list", label: "生成回归清单" },
  { value: "test-report", label: "生成测试报告" },
  { value: "bug-analysis", label: "分析 Bug" },
  { value: "log-triage", label: "排查日志" },
  { value: "sql-analysis", label: "分析 SQL" },
];

interface Page<T> {
  items: T[];
  nextCursor: string | null;
}

export interface CreateSessionDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateSessionDialog({
  open,
  onClose,
  onCreated,
}: CreateSessionDialogProps) {
  const projectsQuery = useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiFetch<Page<Project>>("/projects"),
    enabled: open,
  });
  const modelsQuery = useQuery({
    queryKey: queryKeys.models({ enabled: true }),
    queryFn: () =>
      apiFetch<Page<EnabledModel>>(`/models${queryString({ enabled: true })}`),
    enabled: open,
  });
  const [projectId, setProjectId] = useState("");
  const [modelId, setModelId] = useState("");
  const [title, setTitle] = useState("");
  const [entranceKey, setEntranceKey] = useState("bug-analysis");
  const [submitting, setSubmitting] = useState(false);

  const projects = projectsQuery.data?.items ?? [];
  const models = modelsQuery.data?.items ?? [];
  const missingProjects = projects.length === 0;
  const missingModels = models.length === 0;
  const canSubmit = !missingProjects && !missingModels && title.trim() !== "";

  async function onSubmit() {
    if (!canSubmit) {
      return;
    }
    setSubmitting(true);
    try {
      await apiFetch("/sessions", {
        method: "POST",
        body: JSON.stringify({
          projectId: Number(projectId || projects[0]?.projectId),
          modelId: Number(modelId || models[0]?.modelId),
          title: title.trim(),
          entranceKey,
        }),
      });
      onCreated();
      onClose();
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal open={open} onOpenChange={(next) => !next && onClose()} title="新建会话">
      {missingProjects ? (
        <p>
          还没有项目，请先到 <Link to="/projects">项目</Link> 创建一个。
        </p>
      ) : null}
      {missingModels ? (
        <p>
          没有可用模型，请先到 <Link to="/providers">提供商</Link> 配置并启用模型。
        </p>
      ) : null}
      <div style={{ display: "grid", gap: 12 }}>
        <FormField label="项目" required>
          <Select
            options={projects.map((project) => ({
              value: String(project.projectId),
              label: project.name,
            }))}
            value={projectId}
            onChange={setProjectId}
            placeholder="选择项目"
            disabled={missingProjects}
          />
        </FormField>
        <FormField label="模型" required>
          <Select
            options={models.map((model) => ({
              value: String(model.modelId),
              label: `${model.displayName} · ${model.provider.name}`,
            }))}
            value={modelId}
            onChange={setModelId}
            placeholder="选择模型"
            disabled={missingModels}
          />
        </FormField>
        <FormField label="入口">
          <Select
            options={ENTRANCES}
            value={entranceKey}
            onChange={setEntranceKey}
          />
        </FormField>
        <FormField label="标题" required>
          <Input value={title} onChange={(event) => setTitle(event.target.value)} />
        </FormField>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
        <Button type="button" variant="ghost" onClick={onClose}>
          取消
        </Button>
        <Button
          type="button"
          onClick={() => void onSubmit()}
          disabled={!canSubmit}
          loading={submitting}
        >
          创建
        </Button>
      </div>
    </Modal>
  );
}
