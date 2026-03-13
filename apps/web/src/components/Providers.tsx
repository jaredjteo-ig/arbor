"use client";

import { useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";

/* Initialize i18n (side-effect import) */
import "@/lib/i18n";

/**
 * Create a stable QueryClient instance per component lifecycle.
 * Defaults provide sensible retry/stale behavior for the app.
 */
function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        retry: 1,
        refetchOnWindowFocus: false,
      },
      mutations: {
        retry: 0,
      },
    },
  });
}

/**
 * Client-side provider tree that wraps the entire application.
 * Keeps the root layout as a server component so that metadata exports work.
 *
 * Provider order (outermost → innermost):
 *   QueryClientProvider → AuthProvider → children
 */
export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
}
