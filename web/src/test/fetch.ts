import { vi } from "vitest";

export type MockHandler = (
  request: Request,
  url: URL,
) => Response | Promise<Response>;

export function jsonResponse(
  body: unknown,
  status = 200,
  headers?: HeadersInit,
): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}

function resolveUrl(input: RequestInfo | URL): URL {
  if (input instanceof URL) {
    return input;
  }
  if (typeof input === "string") {
    return new URL(input, "http://localhost");
  }
  return new URL(input.url, "http://localhost");
}

function resolveMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) {
    return init.method.toUpperCase();
  }
  if (typeof input === "object" && input !== null && "method" in input) {
    return String((input as Request).method || "GET").toUpperCase();
  }
  return "GET";
}

export function installFetchMock() {
  const handlers: Array<{
    method: string;
    match: (pathname: string) => boolean;
    impl: MockHandler;
  }> = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = resolveUrl(input);
    const method = resolveMethod(input, init);
    const request = new Request(url, { ...init, method });
    const handler = handlers.find(
      (item) => item.method === method && item.match(url.pathname),
    );
    if (!handler) {
      return jsonResponse(
        {
          code: "not_found",
          message: `no mock for ${method} ${url.pathname}`,
          details: [],
          requestId: "test",
        },
        404,
      );
    }
    return handler.impl(request, url);
  });

  vi.stubGlobal("fetch", fetchMock);

  return {
    fetch: fetchMock,
    on(method: string, path: string | RegExp, impl: MockHandler) {
      handlers.push({
        method: method.toUpperCase(),
        match:
          typeof path === "string"
            ? (pathname) => pathname === path
            : (pathname) => path.test(pathname),
        impl,
      });
    },
  };
}
