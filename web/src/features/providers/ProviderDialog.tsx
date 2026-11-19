import { useState } from "react";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { apiFetch } from "../../lib/api/client";
import { isApiError } from "../../lib/api/errors";
import {
  mapConnectionState,
  type ConnectionTestState,
} from "./ConnectionTestBadge";
import { ProviderForm } from "./ProviderForm";
import type { ConnectionTestResult, Provider, ProviderDraft } from "./types";

function toDraft(provider?: Provider): ProviderDraft {
  return {
    name: provider?.name ?? "",
    protocol: provider?.protocol ?? "openai_compatible",
    baseUrl: provider?.baseUrl ?? "",
    apiKey: "",
    enabled: provider?.enabled ?? true,
  };
}

export interface ProviderDialogProps {
  open: boolean;
  provider?: Provider;
  onClose: () => void;
  onSaved: () => void;
}

export function ProviderDialog({
  open,
  provider,
  onClose,
  onSaved,
}: ProviderDialogProps) {
  const [value, setValue] = useState<ProviderDraft>(() => toDraft(provider));
  const [errors, setErrors] = useState<Partial<Record<keyof ProviderDraft, string>>>(
    {},
  );
  const [testState, setTestState] = useState<ConnectionTestState>("idle");
  const [testResult, setTestResult] = useState<ConnectionTestResult | undefined>();
  const [submitting, setSubmitting] = useState(false);

  function onFormChange(next: ProviderDraft) {
    setValue(next);
    setTestState("idle");
    setTestResult(undefined);
  }

  async function onTest() {
    setTestState("testing");
    try {
      const path = provider
        ? `/providers/${provider.providerId}/connection-test`
        : "/providers/connection-test";
      const body: Record<string, string> = {
        protocol: value.protocol,
        baseUrl: value.baseUrl,
      };
      if (value.apiKey) {
        body.apiKey = value.apiKey;
      }
      const result = await apiFetch<ConnectionTestResult>(path, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setTestResult(result);
      setTestState(mapConnectionState(result));
    } catch {
      setTestState("unreachable");
    }
  }

  async function onSubmit() {
    setSubmitting(true);
    setErrors({});
    const payload: Record<string, unknown> = {
      name: value.name,
      protocol: value.protocol,
      baseUrl: value.baseUrl,
    };
    if (provider) {
      payload.enabled = value.enabled;
      if (value.apiKey) {
        payload.apiKey = value.apiKey;
      }
    } else {
      payload.apiKey = value.apiKey;
    }
    try {
      if (provider) {
        await apiFetch(`/providers/${provider.providerId}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await apiFetch("/providers", {
          method: "POST",
          body: JSON.stringify(payload),
        });
      }
      onSaved();
      onClose();
    } catch (error) {
      if (isApiError(error)) {
        const next: Partial<Record<keyof ProviderDraft, string>> = {};
        for (const key of ["name", "protocol", "baseUrl", "apiKey"] as const) {
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
      title={provider ? "编辑提供商" : "新建提供商"}
    >
      <ProviderForm
        value={value}
        onChange={onFormChange}
        errors={errors}
        maskedValue={provider?.apiKeyMasked}
        testState={testState}
        testResult={testResult}
        onTest={() => void onTest()}
        showEnabled={Boolean(provider)}
      />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}>
        <Button type="button" variant="ghost" onClick={onClose}>
          取消
        </Button>
        <Button type="button" onClick={() => void onSubmit()} loading={submitting}>
          {provider ? "保存" : "创建"}
        </Button>
      </div>
    </Modal>
  );
}
