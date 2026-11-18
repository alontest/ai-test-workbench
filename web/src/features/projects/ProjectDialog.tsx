import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { ProjectForm } from "./ProjectForm";
import type { Project, ProjectDraft } from "./types";

function toDraft(project?: Project): ProjectDraft {
  return {
    name: project?.name ?? "",
    repoUrl: project?.repoUrl ?? "",
    techStack: project?.techStack ?? "",
    requirementSource: project?.requirementSource ?? "",
    notes: project?.notes ?? "",
  };
}

export interface ProjectDialogProps {
  open: boolean;
  project?: Project;
  onClose: () => void;
  onSaved: () => void;
}

export function ProjectDialog({
  open,
  project,
  onClose,
  onSaved,
}: ProjectDialogProps) {
  const [value, setValue] = useState<ProjectDraft>(() => toDraft(project));
  const [errors, setErrors] = useState<Partial<Record<keyof ProjectDraft, string>>>(
    {},
  );
  const [submitting, setSubmitting] = useState(false);

  function reset(next = project) {
    setValue(toDraft(next));
    setErrors({});
  }

  async function onSubmit() {
    setSubmitting(true);
    setErrors({});
    const payload = {
      name: value.name,
      repoUrl: value.repoUrl.trim() === "" ? null : value.repoUrl,
      techStack: value.techStack.trim() === "" ? null : value.techStack,
      requirementSource:
        value.requirementSource.trim() === "" ? null : value.requirementSource,
      notes: value.notes.trim() === "" ? null : value.notes,
    };
    try {
      if (project) {
        await apiFetch(`/projects/${project.projectId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/projects", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      onSaved();
      onClose();
    } catch (error) {
      if (isApiError(error)) {
        const next: Partial<Record<keyof ProjectDraft, string>> = {};
        for (const key of [
          "name",
          "repoUrl",
          "techStack",
          "requirementSource",
          "notes",
        ] as const) {
          const message = error.fieldError(key);
          if (message) {
            next[key] = message;
          }
        }
        if (Object.keys(next).length === 0 && error.message) {
          next.name = error.message;
        }
        setErrors(next);
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onOpenChange={(nextOpen) => {
        if (nextOpen) {
          reset();
        } else {
          onClose();
        }
      }}
      title={project ? "编辑项目" : "新建项目"}
    >
      <ProjectForm value={value} onChange={setValue} errors={errors} />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
        <Button type="button" variant="ghost" onClick={onClose}>
          取消
        </Button>
        <Button type="button" onClick={() => void onSubmit()} loading={submitting}>
          {project ? "保存" : "创建"}
        </Button>
      </div>
    </Modal>
  );
}
