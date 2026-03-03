"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import * as Sentry from "@sentry/nextjs";
import { ReactNode, useEffect, useState } from "react";

type ProvidersProps = {
  children: ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            staleTime: 15_000,
          },
        },
      }),
  );

  useEffect(() => {
    // Emit a low-cardinality startup metric so frontend metrics pipeline is visible in Sentry.
    const metricsApi = (Sentry as unknown as { metrics?: { count?: (name: string, value: number) => void } }).metrics;
    metricsApi?.count?.("frontend.app.mount", 1);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
