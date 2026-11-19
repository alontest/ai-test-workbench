import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import { ModelForm } from "./ModelForm";
import type { ModelBinding, ModelDraft } from "./types";

function toDraft(model?: ModelBinding): ModelDraft {
  return {
    modelName: model?.modelName ?? "",
    displayName: model?.displayName ?? "",
    defaultTemperature: String(model?.defaultTemperature ?? 0.7),
    defaultMaxTokens: String(model?.defaultMaxTokens ?? 4096),
    enabled: model?.enabled ?? true,
  };
}

export interface ModelDialogProps {
  open: boolean;
  providerId: number;
  model?: ModelBinding;
  onClose: () => void;
  onSaved: () => void;
}

export function ModelDialog({
  open,
  providerId,
  model,
  onClose,
  onSaved,
}: ModelDialogProps) {
  const [value, setValue] = useState<ModelDraft>(() => toDraft(model));
  const [errors, setErrors] = useState<Partial<Record<keyof ModelDraft, string>>>(
    {},
  );
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit() {
    setSubmitting(true);
    setErrors({});
    const payload: Record<string, unknown> = {
      displayName: value.displayName,
      defaultTemperature: Number(value.defaultTemperature),
      defaultMaxTokens: Number(value.defaultMaxTokens),
    };
    try {
      if (model) {
        payload.enabled = value.enabled;
        await apiFetch(`/models/${model.modelId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        payload.modelName = value.modelName;
        await apiFetch(`/providers/${providerId}/models`, {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      onSaved();
      onClose();
    } catch (error) {
      if (isApiError(error)) {
        const next: Partial<Record<keyof ModelDraft, string>> = {};
        for (const key of [
          "modelName",
          "displayName",
          "defaultTemperature",
          "defaultMaxTokens",
        ] as const) {
          const message = error.fieldError(key);
          if (message) {
            next[key] = message;
          }
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
        if (!nextOpen) {
          onClose();
        }
      }}
      title={model ? "编辑模型" : "新建模型"}
    >
      <ModelForm
        value={value}
        onChange={setValue}
        errors={errors}
        nameLocked={Boolean(model)}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
        <Button type="button" variant="ghost" onClick={onClose}>
          取消
        </Button>
        <Button type="button" onClick={() => void onSubmit()} loading={submitting}>
          {model ? "保存" : "创建"}
        </Button>
      </div>
    </Modal>
  );
}
