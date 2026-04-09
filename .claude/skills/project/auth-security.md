---
name: auth-security
description: "Authentication and security patterns for Arbor. Use when working on JWT tokens, password handling, tenant isolation, rate limiting, token blocklist, or PDPA compliance."
---

# Authentication & Security

## JWT Token System

### Token Types

| Type           | Expiry                | Key Claims                              | Created By                      |
| -------------- | --------------------- | --------------------------------------- | ------------------------------- |
| Access         | 60 min (configurable) | sub, email, role, company_id, tv, jti   | `create_access_token()`         |
| Refresh        | 7 days                | sub, type="refresh", tv, jti            | `create_refresh_token()`        |
| Password Reset | 1 hour                | sub (email), type="password_reset", jti | `create_password_reset_token()` |

### Token Versioning (Instant Session Termination)

User model has `token_version: int = 1`. All JWTs include a `tv` (token version) claim. The auth middleware checks `tv` against the user's current `token_version` on every request via an in-memory cache (30s TTL).

When `token_version` is incremented, ALL existing tokens for that user are instantly invalidated — no need to enumerate or blocklist individual JTIs.

**Version is incremented on:**
- Employee termination (exit endpoint)
- Password change (settings endpoint)
- Password reset (auth_service)

**Files:**
- `src/hr_advisory/api/middleware/token_version_cache.py` — Thread-safe singleton cache
- `src/hr_advisory/api/middleware/auth_middleware.py` — Version check after blocklist check

**Cache behavior:**
- Cache hit: ~0.1ms (dict lookup)
- Cache miss: ~5ms (one DataFlow read)
- TTL: 30 seconds (configurable)
- Explicit invalidation on termination/password change for instant effect

### Token Blocklist

JTI-based revocation. Two implementations:

- `InMemoryBlocklist` — Dev/test, auto-cleanup of expired entries
- `RedisBlocklist` — Production, persists across restarts

Tokens are blocklisted on:

- Logout (both access + refresh if provided)
- Password reset (after use — single-use)
- Refresh token revocation

File: `src/hr_advisory/api/middleware/token_blocklist.py`

### Rate Limiting

ALL auth endpoints limited to 5 requests/minute per IP. ALL write endpoints (POST/PATCH/DELETE) across 13 routers have `check_rate_limit()` at 30/minute per user (60/minute for alert read/dismiss).

File: `src/hr_advisory/api/middleware/rate_limit.py`

### RBAC

- Backend: `require_role("owner", "hr_manager")` on admin endpoints
- Frontend: `AdminGuard` component on 15 admin pages blocks employees
- Employee nav uses dedicated `/my-*` routes with exact path matching

### PII Encryption

- `PUT /employees/me` encrypts NRIC/bank via `encrypt_field()`, skips masked values (containing `*`)
- `nric_fin_last4` and `bank_account_last4` removed from `SELF_SERVICE_FIELDS` to prevent direct write bypass
- Frontend masks NRIC/bank display using last4 fields, clears on focus for editing

### Employee Termination Security

Exit endpoint (`POST /employees/{id}/exit`) performs 3 deactivation steps:
1. Employee record: `is_active=False`, `confirmation_status="terminated"`
2. User account: `is_active=False`, `token_version` incremented
3. Token version cache invalidated for instant session termination

If User deactivation fails, raises HTTP 500 (fail-loud, not silent success).

**All access paths blocked for terminated users:**
- Email/password login: `is_active` check in authenticate()
- Google OAuth: `is_active` check before token issuance
- Token refresh: `is_active` + `token_version` mismatch check
- Existing access token: `tv` check in auth middleware

### Password Handling

- Hashed with bcrypt via `passlib`
- Minimum 8 characters, maximum 72 (bcrypt truncation limit)
- Email format validated via regex (no reflection in error messages)

## Tenant Isolation

### Company-Level Isolation

```python
from hr_advisory.api.middleware.tenant_isolation import validate_company_access

# In any company-scoped endpoint:
validate_company_access(current_user, requested_company_id=company_id)
```

Rules:

- Users access only their own company's data
- `platform_admin` has cross-company access
- Users without `company_id` denied all company resources
- Document download validates `company_id` against document ownership
- Document history auto-scopes to user's company (non-admin)

### Conversation-Level Isolation

```python
# Module-level ownership tracking (in-memory, MVP)
_conversation_owners: dict[str, str] = {}  # conv_id -> user_id

# Record ownership on creation (in advisory_query / advisory_stream)
_conversation_owners[str(conversation_id)] = str(user_id)

# Verify on access (list, history, delete, rename)
owner = _conversation_owners.get(conv_key, "")
if owner and owner != user_id:
    raise HTTPException(status_code=404, detail="Conversation not found.")
```

Rules:

- Ownership recorded when conversation is first created (query or stream)
- All access endpoints (list, history, delete, rename) verify ownership
- Non-owned conversations return 404 (not 403, to prevent enumeration)
- Delete also cleans up `_conversation_owners` mapping
- In-memory storage — conversations lost on restart (database persistence planned)

File: `src/hr_advisory/api/routers/advisory.py`

## Rate Limiting

Per-category, per-IP/user throttling:

| Category   | /min | /hour | Burst |
| ---------- | ---- | ----- | ----- |
| Advisory   | 10   | 100   | 3     |
| Auth       | 5    | 20    | 2     |
| Calculator | 30   | 500   | 10    |
| Admin      | 20   | 200   | 5     |
| Document   | 10   | 100   | 3     |

File: `src/hr_advisory/workflows/guardrails.py`

In-memory (MVP). Production: Redis-based shared rate limiter.

## Security Headers

Every response includes: X-Content-Type-Options, X-Frame-Options, HSTS, CSP, Referrer-Policy, Permissions-Policy.

## Input Validation

- HTML-escape all user input
- Strip null bytes
- Query length: 3-2,000 characters
- UEN format: 8-10 alphanumeric ending with letter
- Email format validation (no input reflection in errors)

## Production Safeguards

- Startup blocks if `JWT_SECRET_KEY` is default value in production
- Startup blocks if `DEBUG=true` in production
- Error responses use generic messages (no exception details)

## Key Files

- `src/hr_advisory/services/auth_service.py` — Auth business logic
- `src/hr_advisory/api/routers/auth.py` — Auth endpoints
- `src/hr_advisory/api/middleware/auth_middleware.py` — JWT validation
- `src/hr_advisory/api/middleware/token_blocklist.py` — JTI blocklist
- `src/hr_advisory/api/middleware/tenant_isolation.py` — Company access
- `src/hr_advisory/security/validation.py` — Input sanitisation
- `src/hr_advisory/security/pdpa.py` — PDPA compliance
- `src/hr_advisory/security/llm_encryption.py` — BYOK API key encryption (dedicated Fernet key)
- `src/hr_advisory/services/audit_log.py` — PDPA audit events for key lifecycle
- `docs/03-security.md` — Full security documentation
- `docs/00-authority/07-byok-api-keys.md` — BYOK security architecture

## BYOK API Key Security

### Encryption Separation

LLM API keys use a **dedicated** `LLM_KEY_ENCRYPTION_KEY` (Fernet), separate from `SALARY_ENCRYPTION_KEY`. No plaintext fallback in production. Dev mode derives from JWT_SECRET_KEY with warning.

### Key Lifecycle Audit Events

Every key operation is logged via `log_audit_event()` with `AuditAction` constants:

- `LLM_KEY_CREATED`, `LLM_KEY_VIEWED`, `LLM_KEY_DELETED`, `LLM_KEY_VALIDATED`
- `LLM_KEY_STATUS_CHANGED`, `LLM_KEY_DECRYPTED`, `LLM_KEY_ROTATED`
- `LLM_BUDGET_CHANGED`, `LLM_BUDGET_EXCEEDED`

### Context Variable Safety

Per-request LLM context uses `contextvars.ContextVar` (not `threading.local`) + `copy_context().run()` for thread pool dispatch. This prevents cross-tenant key leakage when Kaizen agents spawn child threads.

### SSRF Protection

Ollama base_url validation blocks cloud metadata endpoints (169.254.169.254, metadata.google.internal, 100.100.100.200). Private IPs are intentionally allowed for DGX/institutional use.

### Key Rotation

CLI tool: `OLD_LLM_KEY=... NEW_LLM_KEY=... python -m hr_advisory.cli.rotate_llm_keys`
Process restart required after rotation (lru_cache on Fernet instance).

## Red Team Hardening (Rounds 8-9, 2026-04-06)

**SSRF Prevention**: `_resolve_and_validate_url(url)` in llm_config.py resolves hostname via `socket.getaddrinfo()`, checks each IP against blocked ranges (loopback, private, link-local, metadata, IPv4-mapped IPv6). Applied to Ollama and custom LLM validation.

**Content-Disposition Sanitization**: `_sanitize_filename(title, extension)` strips all chars except `[a-zA-Z0-9\-_. ]`, collapses hyphens, truncates to 100 chars. Applied to all download endpoints (documents, payroll exports, payslip PDFs).

**NaN/Infinity Validation**: `math.isfinite()` required on all monetary values from user input. NaN bypasses all comparisons (`NaN > X` is always `False`). Applied to: claim category limits, parallel CSV upload, constraint fields.

**Rate Limiter Bounds**: `OrderedDict` with `MAX_RATE_KEYS = 50,000` and LRU eviction on middleware + webhook rate limiters. `_generated_docs` bounded to 1,000 entries.

**Role Gating**: See RBAC section below for comprehensive role-page matrix.

## RBAC — Role-Based Access Control (Codified 2026-04-08)

### Four Roles

| Role             | Dashboard       | Sidebar                         | Company-Scoped Data |
| ---------------- | --------------- | ------------------------------- | ------------------- |
| `owner`          | `/dashboard`    | Full management nav             | Own company         |
| `hr_manager`     | `/dashboard`    | Full management nav             | Own company         |
| `consultant`     | `/dashboard`    | Full management nav             | Multiple companies  |
| `employee`       | `/my-dashboard` | "My ..." self-service nav only  | Own records only    |
| `platform_admin` | (backend only)  | N/A — not in frontend User type | Cross-company       |

### Frontend Role Guard Pattern (MANDATORY)

All restricted pages MUST use the **allow-list** pattern (fail-closed). NEVER use deny-list (`=== "employee"`) — new roles would bypass it.

```tsx
// CORRECT — allow-list (fail-closed)
if (user?.role !== "owner" && user?.role !== "hr_manager") {
  return (
    <div className="max-w-6xl mx-auto py-12 text-center">
      <p className="text-[var(--color-gray-500)]">
        Access Denied. You do not have permission to view this page.
      </p>
      <a href="/dashboard"
        className="inline-block mt-4 text-sm text-[var(--color-primary)] hover:underline">
        Return to Dashboard
      </a>
    </div>
  );
}

// WRONG — deny-list (fails open for new roles)
if (user?.role === "employee") { ... }
```

### Guard Placement Rules

1. Guard MUST be placed **after all React hooks** (useState, useEffect, useCallback) to avoid hooks rule violations
2. Guard MUST be placed **before any error-state early returns** — otherwise the error path bypasses RBAC
3. Guard MUST be placed **before the main return** JSX

```
function Page() {
  const { user } = useAuth();        // 1. Hooks first
  const [data, setData] = useState();
  useEffect(() => { ... }, []);

  // 2. RBAC guard (after hooks, before error/loading returns)
  if (user?.role !== "owner" && user?.role !== "hr_manager") {
    return <AccessDenied />;
  }

  // 3. Error/loading states
  if (error) return <ErrorState />;
  if (loading) return <LoadingState />;

  // 4. Main render
  return <PageContent />;
}
```

### Role-Page Matrix (Frontend + Backend)

| Page           | Frontend Guard                            | Backend `require_role`                        |
| -------------- | ----------------------------------------- | --------------------------------------------- |
| `/admin`       | owner, hr_manager                         | owner, hr_manager                             |
| `/employees`   | owner, hr_manager                         | owner, hr_manager                             |
| `/payroll`     | owner, hr_manager (uses `isAdmin`)        | owner, hr_manager                             |
| `/recruitment` | owner, hr_manager, consultant (`isAdmin`) | owner, hr_manager, consultant                 |
| `/profile`     | owner, hr_manager, consultant             | owner, hr_manager, consultant, platform_admin |
| `/clients`     | owner, hr_manager, consultant             | owner, hr_manager, consultant, platform_admin |

### Backend 403 Response

NEVER leak allowed role names in 403 responses. Use generic message:

```python
# CORRECT
raise HTTPException(status_code=403, detail="Insufficient permissions to access this resource.")

# WRONG — leaks role enumeration
raise HTTPException(status_code=403, detail=f"Requires one of: {', '.join(allowed_roles)}")
```

Role details are logged server-side via `logger.warning()` for debugging.

### Defense in Depth

Frontend guards are **client-side only** and can be bypassed via DevTools. Every API endpoint MUST independently enforce `require_role()` regardless of frontend guards. Frontend guards exist for UX (clean "Access Denied" instead of page shells with 403 errors).

### Key Files

- `src/hr_advisory/api/middleware/auth_middleware.py` — `require_role()` factory
- `src/hr_advisory/api/middleware/tenant_isolation.py` — `validate_company_access()`
- `apps/web/src/contexts/AuthContext.tsx` — `useAuth()` hook
- `apps/web/src/components/shell/NavigationSidebar.tsx` — role-based sidebar scoping

## Consult Agent

For security work: use the built-in `security-reviewer` agent
