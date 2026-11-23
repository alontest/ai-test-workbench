import { createBrowserRouter } from "react-router";
import { AppShell } from "./app/AppShell";
import { AuthGate } from "./app/AuthGate";
import { CallsPage } from "./features/calls/CallsPage";
import { LoginPage } from "./features/auth/LoginPage";
import { EntrancePage } from "./features/entrances/EntrancePage";
import { HomePage } from "./features/entrances/HomePage";
import { extensionRoutes } from "./features/extensions/routes";
import { knowledgeRoutes } from "./features/knowledge/routes";
import { ModelsPage } from "./features/models/ModelsPage";
import { ProjectsPage } from "./features/projects/ProjectsPage";
import { ProvidersPage } from "./features/providers/ProvidersPage";
import { repoRoutes } from "./features/repos/routes";
import { SessionDetailPage } from "./features/sessions/SessionDetailPage";
import { SessionsPage } from "./features/sessions/SessionsPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    element: <AuthGate />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/entrances/:key", element: <EntrancePage /> },
          { path: "/providers", element: <ProvidersPage /> },
          { path: "/providers/:id/models", element: <ModelsPage /> },
          { path: "/projects", element: <ProjectsPage /> },
          { path: "/sessions", element: <SessionsPage /> },
          { path: "/sessions/:id", element: <SessionDetailPage /> },
          { path: "/calls", element: <CallsPage /> },
          ...knowledgeRoutes,
          ...repoRoutes,
          ...extensionRoutes,
        ],
      },
    ],
  },
]);
