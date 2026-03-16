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

/* ── Types ────────────────────────────────────────────────── */

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

interface AuthContextValue extends AuthState {
  login: (data: LoginData) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  /** Re-fetch the current user from /auth/me to pick up server-side changes (e.g. company_id). */
  refreshUser: () => Promise<void>;
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
  });

  /* Validate the existing session on mount */
  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      const accessToken = getStoredToken("access_token");
      const refreshToken = getStoredToken("refresh_token");

      if (!accessToken) {
        if (!cancelled) {
          setState({ user: null, isAuthenticated: false, isLoading: false });
        }
        return;
      }

      try {
        const user = await authApi.me(accessToken);
        if (!cancelled) {
          setState({ user, isAuthenticated: true, isLoading: false });
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
              setState({ user, isAuthenticated: true, isLoading: false });
            }
          } catch {
            /* Refresh also failed — clear everything */
            clearTokens();
            if (!cancelled) {
              setState({
                user: null,
                isAuthenticated: false,
                isLoading: false,
              });
            }
          }
        } else {
          clearTokens();
          if (!cancelled) {
            setState({ user: null, isAuthenticated: false, isLoading: false });
          }
        }
      }
    }

    checkAuth();

    return () => {
      cancelled = true;
    };
  }, []);

  /* Login */
  const login = useCallback(
    async (data: LoginData) => {
      const response = await authApi.login(data);
      storeTokens(response.access_token, response.refresh_token);
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
      router.push("/");
    },
    [router],
  );

  /* Register */
  const register = useCallback(
    async (data: RegisterData) => {
      const response = await authApi.register(data);
      storeTokens(response.access_token, response.refresh_token);
      setState({
        user: response.user,
        isAuthenticated: true,
        isLoading: false,
      });
      router.push("/onboarding");
    },
    [router],
  );

  /* Logout */
  const logout = useCallback(() => {
    authApi.logout();
    setState({ user: null, isAuthenticated: false, isLoading: false });
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
      setState({ user, isAuthenticated: true, isLoading: false });
    } catch {
      // Fallback: try with existing access token
      const accessToken = getStoredToken("access_token");
      if (!accessToken) return;
      try {
        const user = await authApi.me(accessToken);
        setState({ user, isAuthenticated: true, isLoading: false });
      } catch {
        /* Silently ignore — user stays as-is */
      }
    }
  }, []);

  return (
    <AuthContext.Provider
      value={{
        ...state,
        login,
        register,
        logout,
        refreshUser,
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
