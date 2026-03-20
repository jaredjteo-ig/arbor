/* ── Base API Client ──────────────────────────────────────── */
/* Reusable HTTP client with automatic auth, token refresh,   */
/* and typed request/response handling.                        */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ── Error class ─────────────────────────────────────────── */

export class ApiRequestError extends Error {
  status: number;
  detail: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.detail = detail ?? message;
  }
}

/* ── Token helpers (client-side only) ────────────────────── */

function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function storeTokens(accessToken: string, refreshToken: string): void {
  localStorage.setItem("access_token", accessToken);
  localStorage.setItem("refresh_token", refreshToken);
}

function clearTokensAndRedirect(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

/**
 * Get a valid access token, refreshing proactively if it will expire soon.
 *
 * Decodes the JWT exp claim and refreshes if less than 5 minutes remain.
 * All raw fetch() callers (useShadowContext, SSE, etc.) should use this
 * instead of reading localStorage directly.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const token = getAccessToken();
  if (!token) return null;

  // Check if token expires within 5 minutes
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    const expiresAt = (payload.exp ?? 0) * 1000;
    const fiveMinutes = 5 * 60 * 1000;
    const maxLifetime = 24 * 60 * 60 * 1000; // 24h sanity bound

    const needsRefresh =
      Date.now() > expiresAt - fiveMinutes || // expiring soon
      expiresAt - Date.now() > maxLifetime; // suspiciously long-lived

    if (needsRefresh) {
      try {
        const newToken = await refreshAccessToken();
        return newToken;
      } catch {
        // Refresh failed — return existing token (will 401, triggering redirect)
        return token;
      }
    }
  } catch {
    // Can't decode — return as-is
  }

  return token;
}

/* ── Token refresh ───────────────────────────────────────── */

/**
 * Singleton refresh promise to avoid multiple concurrent refresh requests
 * when several API calls hit 401 at the same time.
 */
let refreshPromise: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<string> {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new ApiRequestError("No refresh token available", 401);
    }

    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      throw new ApiRequestError("Token refresh failed", response.status);
    }

    const raw = await response.json();
    const tokens = unwrapNexusResponse(raw) as {
      access_token: string;
      refresh_token: string;
    };

    storeTokens(tokens.access_token, tokens.refresh_token || refreshToken);
    return tokens.access_token;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

/* ── Nexus envelope unwrapping ────────────────────────────── */

/**
 * The Nexus gateway wraps successful responses in an envelope:
 *   { data: { content: "{...}" }, status_code: 200, ... }
 * where `content` is the actual JSON response as a string.
 * This function detects and unwraps that envelope.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function unwrapNexusResponse(body: any): any {
  if (
    body &&
    typeof body === "object" &&
    "data" in body &&
    body.data &&
    typeof body.data === "object" &&
    "content" in body.data
  ) {
    const content = body.data.content;
    if (typeof content === "string") {
      try {
        return JSON.parse(content);
      } catch {
        return content;
      }
    }
    return content;
  }
  return body;
}

/* ── Response handler ────────────────────────────────────── */

async function parseErrorBody(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) return body.detail;
  } catch {
    /* response body may not be JSON */
  }

  if (response.status === 400)
    return "Invalid request. Please check your input.";
  if (response.status === 403)
    return "You do not have permission for this action.";
  if (response.status === 404) return "The requested resource was not found.";
  if (response.status >= 500)
    return "A server error occurred. Please try again later.";
  return "An unexpected error occurred.";
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await parseErrorBody(response);
    throw new ApiRequestError(detail, response.status, detail);
  }
  const body = await response.json();
  return unwrapNexusResponse(body) as T;
}

/* ── ApiClient class ─────────────────────────────────────── */

class ApiClient {
  private buildHeaders(accessToken: string | null): HeadersInit {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }
    return headers;
  }

  private buildUrl(path: string, params?: Record<string, string>): string {
    const url = new URL(`${API_BASE}${path}`);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
      }
    }
    return url.toString();
  }

  /**
   * Execute a fetch request with automatic 401 retry via token refresh.
   * On refresh failure, clears tokens and redirects to login.
   */
  private async request<T>(
    method: string,
    path: string,
    options?: {
      body?: unknown;
      params?: Record<string, string>;
    },
  ): Promise<T> {
    const accessToken = getAccessToken();
    const url = this.buildUrl(path, options?.params);

    const fetchOptions: RequestInit = {
      method,
      headers: this.buildHeaders(accessToken),
    };
    if (options?.body !== undefined) {
      fetchOptions.body = JSON.stringify(options.body);
    }

    let response: Response;
    try {
      response = await fetch(url, fetchOptions);
    } catch {
      throw new ApiRequestError(
        "Unable to connect to the server. Please check your internet connection.",
        0,
      );
    }

    /* Handle 401 or 403 — attempt token refresh and retry once.
       403 is included because the JWT may lack a company_id claim that was
       just added server-side (e.g. after company profile creation). */
    if (response.status === 401 || response.status === 403) {
      try {
        const newAccessToken = await refreshAccessToken();
        const retryOptions: RequestInit = {
          method,
          headers: this.buildHeaders(newAccessToken),
        };
        if (options?.body !== undefined) {
          retryOptions.body = JSON.stringify(options.body);
        }
        const retryResponse = await fetch(url, retryOptions);
        return handleResponse<T>(retryResponse);
      } catch {
        if (response.status === 401) {
          clearTokensAndRedirect();
          throw new ApiRequestError(
            "Session expired. Please log in again.",
            401,
          );
        }
        // For 403, surface the original error rather than logging out
        return handleResponse<T>(response);
      }
    }

    return handleResponse<T>(response);
  }

  async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>("GET", path, { params });
  }

  async post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, { body });
  }

  async put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PUT", path, { body });
  }

  async patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, { body });
  }

  async delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  /**
   * POST with FormData (file uploads). Does NOT set Content-Type —
   * the browser adds the correct multipart/form-data boundary automatically.
   */
  async postFormData<T>(path: string, formData: FormData): Promise<T> {
    const accessToken = getAccessToken();
    const url = this.buildUrl(path);

    const headers: Record<string, string> = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    let response: Response;
    try {
      response = await fetch(url, {
        method: "POST",
        headers,
        body: formData,
      });
    } catch {
      throw new ApiRequestError(
        "Unable to connect to the server. Please check your internet connection.",
        0,
      );
    }

    if (response.status === 401 || response.status === 403) {
      try {
        const newAccessToken = await refreshAccessToken();
        const retryResponse = await fetch(url, {
          method: "POST",
          headers: { Authorization: `Bearer ${newAccessToken}` },
          body: formData,
        });
        return handleResponse<T>(retryResponse);
      } catch {
        if (response.status === 401) {
          clearTokensAndRedirect();
          throw new ApiRequestError(
            "Session expired. Please log in again.",
            401,
          );
        }
        return handleResponse<T>(response);
      }
    }

    return handleResponse<T>(response);
  }
}

export const apiClient = new ApiClient();
