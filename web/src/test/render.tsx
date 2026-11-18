import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { MemoryRouter } from "react-router";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

interface RenderWithAppOptions extends Omit<RenderOptions, "wrapper"> {
  route?: string;
  routes?: ReactNode;
}

export function renderWithApp(
  ui: ReactElement,
  { route = "/", routes, ...options }: RenderWithAppOptions = {},
) {
  const client = createTestQueryClient();
  return {
    client,
    ...render(ui, {
      wrapper: ({ children }) => (
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[route]}>
            {routes ?? children}
          </MemoryRouter>
        </QueryClientProvider>
      ),
      ...options,
    }),
  };
}
