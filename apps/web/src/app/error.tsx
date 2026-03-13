"use client";

import { useEffect } from "react";
import { ErrorState } from "@/components/design-system";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <ErrorState
        variant="server"
        title="Something went wrong"
        description="We encountered an unexpected error. Please try again or contact support if the problem persists."
        onRetry={reset}
        retryLabel="Try again"
      />
    </div>
  );
}
