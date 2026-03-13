/* ── Auth API Client ─────────────────────────────────────── */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Types ────────────────────────────────────────────────── */

export interface User {
  id: number;
  email: string;
  name: string;
  role: "owner" | "hr_manager" | "consultant";
  company_id: number | null;
}

export interface RegisterData {
  name: string;
  email: string;
  password: string;
}

export interface LoginData {
  email: string;
  password: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export class AuthError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AuthError";
    this.status = status;
  }
}

/* ── Helpers ──────────────────────────────────────────────── */

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = "An unexpected error occurred";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      /* response body may not be JSON */
    }
    throw new AuthError(message, response.status);
  }
  return response.json() as Promise<T>;
}

function authHeaders(accessToken: string): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${accessToken}`,
  };
}

/* ── API Methods ─────────────────────────────────────────── */

export const authApi = {
  register(data: RegisterData): Promise<AuthResponse> {
    return fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<AuthResponse>(res));
  },

  login(data: LoginData): Promise<AuthResponse> {
    return fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((res) => handleResponse<AuthResponse>(res));
  },

  refresh(refreshToken: string): Promise<AuthTokens> {
    return fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).then((res) => handleResponse<AuthTokens>(res));
  },

  me(accessToken: string): Promise<User> {
    return fetch(`${API_BASE}/auth/me`, {
      method: "GET",
      headers: authHeaders(accessToken),
    }).then((res) => handleResponse<User>(res));
  },

  requestPasswordReset(email: string): Promise<{ message: string }> {
    return fetch(`${API_BASE}/auth/forgot-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    }).then((res) => handleResponse<{ message: string }>(res));
  },

  resetPassword(token: string, password: string): Promise<{ message: string }> {
    return fetch(`${API_BASE}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password }),
    }).then((res) => handleResponse<{ message: string }>(res));
  },

  async logout(): Promise<void> {
    if (typeof window !== "undefined") {
      const accessToken = localStorage.getItem("access_token");
      const refreshToken = localStorage.getItem("refresh_token");

      // Call backend revocation endpoint before clearing local state
      if (accessToken) {
        try {
          await fetch(`${API_BASE}/auth/logout`, {
            method: "POST",
            headers: authHeaders(accessToken),
            body: JSON.stringify({ refresh_token: refreshToken || "" }),
          });
        } catch {
          // Best-effort: clear local tokens even if backend call fails
        }
      }

      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  },
};
