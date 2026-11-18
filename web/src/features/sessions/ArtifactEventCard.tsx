import { ArtifactCard } from "../composer/ArtifactCard";
import type { ArtifactEventPayload } from "./types";

export interface ArtifactEventCardProps {
  payload: ArtifactEventPayload;
}

export function ArtifactEventCard({ payload }: ArtifactEventCardProps) {
  return (
    <ArtifactCard
      artifactId={payload.artifactId}
      fileName={payload.fileName}
      byteSize={payload.byteSize}
    />
  );
}
