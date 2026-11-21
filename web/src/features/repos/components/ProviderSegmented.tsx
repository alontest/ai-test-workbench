import type { RepoProvider } from "../api/types";
import { PROVIDER_LABELS } from "../api/types";
import styles from "./repo.module.css";

const PROVIDERS: RepoProvider[] = ["yunxiao", "github"];

export interface ProviderSegmentedProps {
  value: RepoProvider;
  onChange: (value: RepoProvider) => void;
  disabled?: boolean;
}

export function ProviderSegmented({
  value,
  onChange,
  disabled,
}: ProviderSegmentedProps) {
  return (
    <div className={styles.segmented} role="group" aria-label="提供商">
      {PROVIDERS.map((provider) => (
        <button
          key={provider}
          type="button"
          className={value === provider ? styles.segmentActive : undefined}
          aria-pressed={value === provider}
          disabled={disabled}
          onClick={() => onChange(provider)}
        >
          {PROVIDER_LABELS[provider]}
        </button>
      ))}
    </div>
  );
}
