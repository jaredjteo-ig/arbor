---
name: auth-security
description: "Authentication and security patterns for Arbor. Use when working on JWT tokens, password handling, tenant isolation, rate limiting, token blocklist, or PDPA compliance."
---

# Authentication & Security

## JWT Token System

### Token Types

| Type           | Expiry                | Key Claims                              | Created By                      |
| -------------- | --------------------- | --------------------------------------- | ------------------------------- |
| Access         | 60 min (configurable) | sub, email, role, company_id, jti       | `create_access_token()`         |
| Refresh        | 7 days                | sub, type="refresh", jti                | `create_refresh_token()`        |
| Password Reset | 1 hour                | sub (email), type="password_reset", jti | `create_password_reset_token()` |

### Token Blocklist

JTI-based revocation. Two implementations:

- `InMemoryBlocklist` — Dev/test, auto-cleanup of expired entries
- `RedisBlocklist` — Production, persists across restarts

Tokens are blocklisted on:

- Logout (both access + refresh if provided)
- Password reset (after use — single-use)
- Refresh token revocation

File: `src/hr_advisory/api/middleware/token_blocklist.py`

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

## Consult Agent

For security work: use the built-in `security-reviewer` agent
