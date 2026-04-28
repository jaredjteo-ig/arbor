"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import {
  authApi,
  AuthError,
  type User,
  type RegisterData,
  type LoginData,
} from "@/services/api/auth";
import {
  featureFlagsApi,
  DEFAULT_FEATURE_FLAGS,
  type FeatureFlags,
  type FeatureFlagKey,
} from "@/services/api/feature_flags";

/* ── Types ────────────────────────────────────────────────── */

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  /** Latest server-side feature flags for the user's company. */
  featureFlags: FeatureFlags;
  /** True until the first feature-flag fetch resolves (success or fail). */
  featureFlagsLoaded: boolean;
}

interface AuthContextValue extends AuthState {
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  /** Re-fetch the current user from /auth/me to pick up server-side changes (e.g. company_id). */
  refreshUser: () => Promise<void>;
  /** Store pre-obtained tokens (e.g. from employee invite signup) and hydrate auth state. */
  loginWithTokens: (
    accessToken: string,
    refreshToken: string,
    user: User,
  ) => void;
  /** Refresh the cached feature-flag map from the server. */
  refreshFeatureFlags: () => Promise<void>;
  /**
   * Persist a flag change to the backend (owner-only). Throws on failure
   * so the caller can show a toast — we deliberately don't swallow.
   */
  setFeatureFlag: (name: FeatureFlagKey, value: boolean) => Promise<void>;
}

/* ── Context ──────────────────────────────────────────────── */

const AuthContext = createContext<AuthContextValue | null>(null);

/* ── Token helpers ────────────────────────────────────────── */

function getStoredToken(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key);
}

function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

function clearTokens(): void {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

/* ── Provider ─────────────────────────────────────────────── */

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    featureFlags: { ...DEFAULT_FEATURE_FLAGS },
    featureFlagsLoaded: false,
  });

  /* Fetch feature flags from the backend and stash them in context.
     We never fall back to localStorage — if the API is down, defaults
     stay off. The first call after login/refresh sets featureFlagsLoaded
     so callers can distinguish "not loaded yet" from "loaded, all off". */
  const loadFeatureFlags = useCallback(async () => {
    try {
      const res = await featureFlagsApi.get();
      setState((prev) => ({
        ...prev,
        featureFlags: { ...DEFAULT_FEATURE_FLAGS, ...res.flags },
        featureFlagsLoaded: true,
      }));
    } catch {
      // Network failure / 401 / 403 — leave flags at default (off) and
      // mark as loaded so the UI renders rather than blocking forever.
      setState((prev) => ({
        ...prev,
        featureFlags: { ...DEFAULT_FEATURE_FLAGS },
        featureFlagsLoaded: true,
      }));
    }
  }, []);

  /* Proactive token refresh — refresh 5 minutes before expiry.
     This prevents the "silent 401" problem where background requests
     fail because the token expired between user interactions.

     Uses refreshAccessToken() singleton from client.ts to avoid
     concurrent refresh collisions with apiClient/SSE retry paths. */
  useEffect(() => {
    let cancelled = false;

    function scheduleRefresh(): ReturnType<typeof setTimeout> | undefined {
      const accessToken = getStoredToken("access_token");
      if (!accessToken || !getStoredToken("refresh_token")) return undefined;

      try {
        const payload = JSON.parse(atob(accessToken.split(".")[1]));
        const expiresAt = (payload.exp ?? 0) * 1000;
        const maxLifetime = 24 * 60 * 60 * 1000; // 24h sanity bound
        if (expiresAt - Date.now() > maxLifetime) {
          // Suspiciously long-lived token — force refresh
          doRefresh();
          return undefined;
        }

        const refreshAt = expiresAt - 5 * 60 * 1000; // 5 min before expiry
        const delay = refreshAt - Date.now();

        if (delay <= 0) {
          doRefresh();
          return undefined;
        }

        return setTimeout(() => doRefresh(), delay);
      } catch {
        return undefined;
      }
    }

    async function doRefresh() {
      if (cancelled) return;
      try {
        // Read fresh refresh token inside callback, not from closure
        const { refreshAccessToken } = await import("@/services/api/client");
        const newToken = await refreshAccessToken();
        if (cancelled) return;
        // Re-schedule for the new token
        if (newToken) scheduleRefresh();
      } catch {
        if (cancelled) return;
        clearTokens();
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          featureFlags: DEFAULT_FEATURE_FLAGS,
          featureFlagsLoaded: false,
        });
      }
    }

    const timer = scheduleRefresh();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [state.isAuthenticated]);

  /* Validate the existing session on mount */
  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      const accessToken = getStoredToken("access_token");
      const refreshToken = getStoredToken("refresh_token");

      if (!accessToken) {
        if (!cancelled) {
          setState({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            featureFlags: DEFAULT_FEATURE_FLAGS,
            featureFlagsLoaded: false,
          });
        }
        return;
      }

      try {
        const user = await authApi.me(accessToken);
        if (!cancelled) {
          setState((prev) => ({
            ...prev,
            user,
            isAuthenticated: true,
            isLoading: false,
          }));
          // Hydrate feature flags after auth resolves. Errors here are
          // non-fatal — the loader catches and falls back to defaults.
          loadFeatureFlags();
        }
      } catch (error) {
        /* If the access token is expired, try to refresh */
        if (
          error instanceof AuthError &&
          error.status === 401 &&
          refreshToken
        ) {
          try {
            const tokens = await authApi.refresh(refreshToken);
            storeTokens(tokens.access_token, tokens.refresh_token);
            const user = await authApi.me(tokens.access_token);
            if (!cancelled) {
              setState((prev) => ({
                ...prev,
                user,
                isAuthenticated: true,
                isLoading: false,
              }));
              loadFeatureFlags();
            }
          } catch {
            /* Refresh also failed — clear everything */
            clearTokens();
            if (!cancelled) {
              setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
                featureFlags: { ...DEFAULT_FEATURE_FLAGS },
                featureFlagsLoaded: false,
              });
            }
          }
        } else {
          clearTokens();
          if (!cancelled) {
            setState({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              featureFlags: { ...DEFAULT_FEATURE_FLAGS },
              featureFlagsLoaded: false,
            });
          }
        }
      }
    }

    checkAuth();

    return () => {
      cancelled = true;
    };
  }, [loadFeatureFlags]);

  /* Login */
  const login = useCallback(
    async (data: LoginData) => {
      const response = await authApi.login(data);
      storeTokens(response.access_token, response.refresh_token);
      setState((prev) => ({
        ...prev,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      }));
      // Pull the freshly-logged-in user's feature flags. Best-effort.
      loadFeatureFlags();
      // Route employees to their personal dashboard; admins to the main dashboard
      const destination =
        response.user.role === "employee" ? "/my-dashboard" : "/dashboard";
      router.push(destination);
    },
    [router, loadFeatureFlags],
  );

  /* Register */
  const register = useCallback(
    async (data: RegisterData) => {
      const response = await authApi.register(data);
      storeTokens(response.access_token, response.refresh_token);
      setState((prev) => ({
        ...prev,
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      }));
      // Fresh registration has no company yet — the API returns defaults
      // and `defaulted: true`. The onboarding page reads `user.company_id`
      // directly to decide chat-vs-form, so this is informational.
      loadFeatureFlags();
      router.push("/onboarding");
    },
    [router, loadFeatureFlags],
  );

  /* Logout */
  const logout = useCallback(() => {
    authApi.logout();
    setState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      featureFlags: { ...DEFAULT_FEATURE_FLAGS },
      featureFlagsLoaded: false,
    });
    router.push("/login");
  }, [router]);

  /* Refresh user — exchange refresh token for a new access token (picks up
     server-side changes like company_id), then re-fetch user from /auth/me. */
  const refreshUser = useCallback(async () => {
    const refreshToken = getStoredToken("refresh_token");
    if (!refreshToken) return;
    try {
      // Get a new access token that includes updated claims (e.g. company_id)
      const tokens = await authApi.refresh(refreshToken);
      storeTokens(tokens.access_token, tokens.refresh_token || refreshToken);
      // Fetch the full user profile with the new token
      const user = await authApi.me(tokens.access_token);
      setState((prev) => ({
        ...prev,
        user,
        isAuthenticated: true,
        isLoading: false,
      }));
      // company_id may have just been populated (post-onboarding); reload flags.
      loadFeatureFlags();
    } catch {
      // Fallback: try with existing access token
      const accessToken = getStoredToken("access_token");
      if (!accessToken) return;
      try {
        const user = await authApi.me(accessToken);
        setState((prev) => ({
          ...prev,
          user,
          isAuthenticated: true,
          isLoading: false,
        }));
        loadFeatureFlags();
      } catch {
        /* Silently ignore — user stays as-is */
      }
    }
  }, [loadFeatureFlags]);

  /* Login with pre-obtained tokens (e.g. from employee invite signup) */
  const loginWithTokens = useCallback(
    (accessToken: string, refreshToken: string, user: User) => {
      storeTokens(accessToken, refreshToken);
      setState((prev) => ({
        ...prev,
        user,
        isAuthenticated: true,
        isLoading: false,
      }));
      loadFeatureFlags();
    },
    [loadFeatureFlags],
  );

  /* Persist a flag change. Owner-only on the server side. */
  const setFeatureFlag = useCallback(
    async (name: FeatureFlagKey, value: boolean) => {
      // Optimistic update so the UI feels responsive; reverted on failure.
      setState((prev) => ({
        ...prev,
        featureFlags: { ...prev.featureFlags, [name]: value },
      }));
      try {
        const res = await featureFlagsApi.update({ [name]: value });
        setState((prev) => ({
          ...prev,
          featureFlags: { ...DEFAULT_FEATURE_FLAGS, ...res.flags },
          featureFlagsLoaded: true,
        }));
      } catch (err) {
        // Revert and bubble up so the caller can toast the user.
        setState((prev) => ({
          ...prev,
          featureFlags: { ...prev.featureFlags, [name]: !value },
        }));
        throw err;
      }
    },
    [],
  );

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshUser,
        loginWithTokens,
        refreshFeatureFlags: loadFeatureFlags,
        setFeatureFlag,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/* ── Hook ─────────────────────────────────────────────────── */

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

/**
 * Read a single feature flag from auth context. Defaults to ``false`` when
 * the flags haven't loaded yet or the API call failed — matching the
 * server-side default. NEVER falls back to localStorage.
 */
export function useFeatureFlag(name: FeatureFlagKey): boolean {
  const { featureFlags } = useAuth();
  return Boolean(featureFlags[name]);
}
