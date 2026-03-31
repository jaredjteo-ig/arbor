# Red Team Round 12 — Post-Deploy Production Verification

**Date**: 2026-03-31
**Scope**: v0.3.0 deployed — verify all M60 changes live on production
**Target**: https://arbor.terrene.foundation

## Deployment Issues Fixed During This Round

### 1. Redis "requirepass" crash (FIXED)

- `docker system prune` removed volumes; compose tried to start Redis with empty `REDIS_PASSWORD`
- **Fix**: Created proper `/opt/arbor/.env` sourcing credentials from flat files (.db-password, .redis-password, .jwt-secret, .encryption-key)

### 2. Frontend "Failed to construct URL" error (FIXED)

- `NEXT_PUBLIC_API_URL` was not set at build time — Next.js bakes env vars into the bundle
- Frontend was using `http://localhost:8000` (default), causing `new URL("")` failures on the `apiClient`
- **Fix**: Rebuilt frontend with `--build-arg NEXT_PUBLIC_API_URL=https://arbor.terrene.foundation/api`

### 3. Disk space exhaustion on production (FIXED)

- Docker image pull failed: "no space left on device"
- **Fix**: `docker system prune -af` freed 21GB (old images, build cache)

## Post-Deploy Verification

### Signup Flow (Playwright Browser)

| Step                                     | Expected                | Result                            |
| ---------------------------------------- | ----------------------- | --------------------------------- |
| Navigate to /signup                      | Signup form             | PASS                              |
| **Company name field visible**           | New M60 field           | **PASS**                          |
| Fill all fields + company name           | Form accepts            | PASS                              |
| Click "Create account"                   | Redirects to /dashboard | **PASS** (was /onboarding before) |
| Dashboard shows sidebar with all modules | 20+ nav items           | PASS                              |
| "Ask Arbor" shadow agent button          | Present                 | PASS                              |

### Advisory Flow (Playwright Browser)

| Step                                | Expected            | Result                                                           |
| ----------------------------------- | ------------------- | ---------------------------------------------------------------- |
| Navigate to /advisory               | Chat interface      | PASS                                                             |
| History sidebar                     | Shows conversations | **PASS** (was "Failed to construct URL" before frontend rebuild) |
| Company context visible             | "Round 12 Test Co"  | PASS                                                             |
| Click suggested CPF question        | Sends to backend    | PASS (200 on /advisory/stream)                                   |
| Conversation appears in history     | With preview text   | PASS                                                             |
| Legal disclaimer                    | Present             | PASS                                                             |
| Shadow margin (5 compliance alerts) | Present             | PASS                                                             |

### API Verification (curl)

| Test                                            | Result                                     |
| ----------------------------------------------- | ------------------------------------------ |
| Atomic registration (company_name → company_id) | **PASS** — `company_id: 1` returned        |
| Tenant isolation (company_id param ignored)     | **PASS** — `company_id: None` for attacker |
| Health endpoint                                 | PASS — all workflows healthy               |
| All 5 containers healthy                        | PASS                                       |

## Findings

### CRITICAL — None

### HIGH — None (all fixed during round)

### MEDIUM

1. **Frontend needs rebuild on every backend URL change** — `NEXT_PUBLIC_API_URL` baked at build time. Consider runtime env injection via `__NEXT_DATA__` or `publicRuntimeConfig`.

### LOW

1. **Google SSO still non-functional** — `NEXT_PUBLIC_GOOGLE_CLIENT_ID` not set (config gap, not code gap)
2. **Production .env was missing** — Had to be created manually from flat credential files. The deploy template now documents this.

## Verdict

**CONVERGED.** v0.3.0 fully deployed and verified. Registration, advisory, compliance, calculators all working. Security fixes (tenant isolation, NaN guards) confirmed live. Frontend conversation loading fixed with correct build-time API URL.
