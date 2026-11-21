import { RepoBrowseIndexPage } from "./pages/RepoBrowseIndexPage";
import { RepoBrowsePage } from "./pages/RepoBrowsePage";

export const repoRoutes = [
  { path: "/repos", element: <RepoBrowseIndexPage /> },
  {
    path: "/projects/:projectId/repos/:bindingId",
    element: <RepoBrowsePage />,
  },
];
