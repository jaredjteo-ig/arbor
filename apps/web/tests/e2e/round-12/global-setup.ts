/**
 * Round-12 global setup: login once, write token to a temp file.
 * All test files read from this file to avoid hitting the auth rate limiter
 * (5 req/min per IP).
 */

import * as fs from "fs";
import * as path from "path";

const API_BASE = "http://localhost:8000";
const TOKEN_FILE = path.join(__dirname, ".auth-token.json");

export default async function globalSetup() {
  // Small delay to ensure any previous rate-limit window has cleared
  await new Promise((r) => setTimeout(r, 1000));

  const resp = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "demo@central.kailash.ai",
      password: "CentralDemo2026!",
    }),
  });

  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(
      `[global-setup] Login failed: HTTP ${resp.status} — ${text}`,
    );
  }

  const body = (await resp.json()) as {
    access_token: string;
    refresh_token: string;
    user?: { id: number; company_id: number };
  };

  fs.writeFileSync(
    TOKEN_FILE,
    JSON.stringify({
      accessToken: body.access_token,
      refreshToken: body.refresh_token,
      userId: body.user?.id ?? 1,
      companyId: body.user?.company_id ?? 1,
      fetchedAt: Date.now(),
    }),
    "utf-8",
  );

  console.log(`[global-setup] Token obtained and cached to ${TOKEN_FILE}`);
}
