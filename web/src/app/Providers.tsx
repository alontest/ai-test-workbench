import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router";
import { subscribeUnauthorized } from "../lib/api/client";
import { safeNextPath } from "../lib/safeNext";

function createClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failureCount, error) => {
          const status = (error as { status?: number }).status;
          if (status === 401 || status === 403 || status === 404) {
            return false;
          }
          return failureCount < 1;
        },
        refetchOnWindowFocus: false,
      },
      mutations: { retry: false },
    },
  });
}

export function UnauthorizedBridge() {
  const navigate = useNavigate();
  useEffect(() => {
    return subscribeUnauthorized((next) => {
      const safe = safeNextPath(next);
      navigate(`/login?next=${encodeURIComponent(safe)}&reason=expired`, {
        replace: true,
      });
    });
  }, [navigate]);
  return null;
}

function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(createClient);
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

export function AppProviders({ children }: { children: ReactNode }) {
  return <Providers>{children}</Providers>;
}
