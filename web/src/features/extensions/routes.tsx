import type { RouteObject } from "react-router";
import { ApprovalsPage } from "./ApprovalsPage";
import { PlannedExtensionPage } from "./PlannedExtensionPage";
import { SkillsPage } from "./SkillsPage";

export const extensionRoutes: RouteObject[] = [
  { path: "/extensions/skills", element: <SkillsPage /> },
  { path: "/extensions/approvals", element: <ApprovalsPage /> },
  { path: "/extensions/:key", element: <PlannedExtensionPage /> },
];
