import { KnowledgeBaseListPage } from "./pages/KnowledgeBaseListPage";
import { KnowledgeBrowsePage } from "./pages/KnowledgeBrowsePage";
import { KnowledgeEntryPage } from "./pages/KnowledgeEntryPage";
import { KnowledgeImportPage } from "./pages/KnowledgeImportPage";

export const knowledgeRoutes = [
  { path: "/knowledge-bases", element: <KnowledgeBaseListPage /> },
  { path: "/knowledge-bases/import", element: <KnowledgeImportPage /> },
  { path: "/knowledge-bases/:kbId", element: <KnowledgeBrowsePage /> },
  {
    path: "/knowledge-bases/:kbId/entries/:code",
    element: <KnowledgeEntryPage />,
  },
];
