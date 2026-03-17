"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { authApi } from "@/services/api/auth";

/**
 * OAuth callback page.
 *
 * Google redirects here with ?code=...&state=... after user authorizes.
 * Validates the CSRF state token, then exchanges the code for AITE tokens.
 */
function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (code) {
      // Validate CSRF state token before exchanging
      if (!authApi.validateOAuthState(state)) {
        router.push("/login?error=sso_failed");
        return;
      }

      authApi
        .googleExchange(code)
        .then((response) => {
          localStorage.setItem("access_token", response.access_token);
          localStorage.setItem("refresh_token", response.refresh_token);
          // Full page navigation (not router.push) so AuthProvider re-mounts
          // and picks up the new tokens from localStorage
          window.location.href = "/";
        })
        .catch(() => {
          router.push("/login?error=sso_failed");
        });
    } else {
      router.push("/login?error=sso_failed");
    }
  }, [router, searchParams]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-primary)] border-t-transparent" />
        <p className="text-sm text-[var(--color-gray-500)]">
          Signing you in...
        </p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-[var(--color-primary)] border-t-transparent" />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
