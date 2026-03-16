"use client";

import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { authApi } from "@/services/api/auth";

/**
 * OAuth callback page.
 *
 * Handles two flows:
 * 1. Google redirects here with ?code=... — exchanges the code for AITE tokens
 * 2. Legacy: backend redirects with ?access_token=...&refresh_token=...
 */
function CallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const code = searchParams.get("code");
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");

    if (code) {
      // Google OAuth flow: exchange code for AITE tokens
      const redirectUri = `${window.location.origin}/auth/callback`;
      authApi
        .googleExchange(code, redirectUri)
        .then((response) => {
          localStorage.setItem("access_token", response.access_token);
          localStorage.setItem("refresh_token", response.refresh_token);
          window.history.replaceState({}, "", "/auth/callback");
          router.push("/");
        })
        .catch(() => {
          router.push("/login?error=sso_failed");
        });
    } else if (accessToken && refreshToken) {
      // Legacy flow: tokens passed directly
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
      window.history.replaceState({}, "", "/auth/callback");
      router.push("/");
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
