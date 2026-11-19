import { ApiError } from "./errors";

const API_PREFIX = "/api/v1";

type UnauthorizedListener = (next: string) => void;

const unauthorizedListeners = new Set<UnauthorizedListener>();

export function subscribeUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

function emitUnauthorized(next: string) {
  for (const listener of unauthorizedListeners) {
    listener(next);
  }
}

export function queryString(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") {
      continue;
    }
    search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const isForm = typeof FormData !== "undefined" && init.body instanceof FormData;
  if (init.body && !isForm && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text) as unknown;
    } catch {
      data = { message: text };
    }
  }
  if (!response.ok) {
    const error = ApiError.from(response.status, data);
    if (
      error.code === "unauthorized" &&
      path !== "/auth/login" &&
      path !== "/auth/session"
    ) {
      emitUnauthorized(
        `${window.location.pathname}${window.location.search}`,
      );
    }
    throw error;
  }
  return data as T;
}

export async function apiFetchText(
  path: string,
  init: RequestInit = {},
): Promise<string> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    credentials: "same-origin",
  });
  const text = await response.text();
  if (!response.ok) {
    let data: unknown = null;
    if (text) {
      try {
        data = JSON.parse(text) as unknown;
      } catch {
        data = { message: text };
      }
    }
    throw ApiError.from(response.status, data);
  }
  return text;
}

export async function apiFetchBlob(
  path: string,
  init: RequestInit = {},
): Promise<Blob> {
  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const text = await response.text();
    let data: unknown = null;
    if (text) {
      try {
        data = JSON.parse(text) as unknown;
      } catch {
        data = { message: text };
      }
    }
    throw ApiError.from(response.status, data);
  }
  return response.blob();
}
