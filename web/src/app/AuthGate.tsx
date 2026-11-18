import { useQuery } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation } from "react-router";
import { Spinner } from "../components/ui/Loading";
import { apiFetch } from "../lib/api/client";
import { queryKeys } from "../lib/api/keys";
import { safeNextPath } from "../lib/safeNext";

interface SessionResponse {
  authenticated: boolean;
  lastSeenAt: string;
  idleExpiresAt: string;
}

export function AuthGate() {
  const location = useLocation();
  const session = useQuery({
    queryKey: queryKeys.session,
    queryFn: () => apiFetch<SessionResponse>("/auth/session"),
  });

  if (session.isPending) {
    return <Spinner label="正在校验登录状态" />;
  }

  if (session.isError || !session.data?.authenticated) {
    const current = `${location.pathname}${location.search}`;
    const next = safeNextPath(current);
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />;
  }

  return <Outlet />;
}
