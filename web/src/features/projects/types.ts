export interface Project {
  projectId: number;
  name: string;
  repoUrl: string | null;
  techStack: string | null;
  requirementSource: string | null;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ProjectDraft {
  name: string;
  repoUrl: string;
  techStack: string;
  requirementSource: string;
  notes: string;
}
