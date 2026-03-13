# Security Architecture

## Authentication

### JWT with JTI + Server-Side Blocklist

The platform uses JWT tokens (HS256) with a unique JTI (JWT ID) claim per token. On logout, the token's JTI is added to a server-side blocklist, preventing reuse even before natural expiry.

**Token types**:

- **Access token** -- Short-lived (configurable via `JWT_EXPIRY_MINUTES`, default 60 minutes)
- **Refresh token** -- Longer-lived, exchangeable for new access tokens
- **Password reset token** -- Single-use, time-limited

**Production safeguards**:

- Startup blocks if `JWT_SECRET_KEY` is the default value in production
- Startup blocks if `DEBUG=true` in production

**Token blocklist**:

- In-memory implementation with automatic expiry cleanup
- Redis-backed implementation when `REDIS_URL` is configured (persists across restarts)
- Thread-safe with periodic cleanup of expired entries

### Password Handling

Passwords are hashed with bcrypt via `passlib`. Minimum length enforced. Email format validated via regex.

### Rate Limiting on Auth Endpoints

Auth endpoints (`/auth/*`) are rate-limited by client IP to prevent brute-force attacks:

- 5 requests/minute
- 20 requests/hour
- Burst limit: 2

Password reset always returns 200 regardless of whether the email exists, preventing email enumeration.

## Authorization

### Tenant Isolation

Every request that accesses company-scoped data validates that the authenticated user belongs to the target company. This is enforced at the middleware level via `validate_company_access()`.

**Rules**:

- Users can only access their own company's data
- `platform_admin` role has cross-company access
- Users without a `company_id` in their JWT are denied access to any company-specific resource

### Role-Based Access Control

Admin and learning pipeline endpoints require `owner` or `hr_manager` role, enforced via `require_role()` dependency.

## Input Security

### Input Sanitisation

All user input is sanitised before processing:

- HTML-escaped to prevent XSS (`html.escape()` with quote escaping)
- Null bytes stripped
- Truncated to maximum length (2,000 characters for advisory queries)

### Query Length Validation

- Minimum: 3 characters
- Maximum: 2,000 characters

### UEN Validation

Singapore Unique Entity Number format: 8-10 alphanumeric characters ending with a letter.

### Email Validation

Standard email format validation via regex pattern.

## Rate Limiting

Per-category rate limits:

| Category   | Requests/min | Requests/hour | Burst |
| ---------- | ------------ | ------------- | ----- |
| Advisory   | 10           | 100           | 3     |
| Calculator | 30           | 500           | 10    |
| Auth       | 5            | 20            | 2     |
| Admin      | 20           | 200           | 5     |
| Document   | 10           | 100           | 3     |

## CORS Hardening

CORS is configured with explicit allowed origins (no wildcards):

- Allowed origins: Configured via `CORS_ORIGINS` environment variable
- Allowed methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
- Allowed headers: Authorization, Content-Type, X-Request-ID (explicit -- no wildcard)
- Credentials: Allowed
- Max age: 3600 seconds

## Security Headers

Every HTTP response includes:

| Header                      | Value                                        |
| --------------------------- | -------------------------------------------- |
| `X-Content-Type-Options`    | `nosniff`                                    |
| `X-Frame-Options`           | `DENY`                                       |
| `X-XSS-Protection`          | `0` (modern browsers use CSP)                |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains`        |
| `Content-Security-Policy`   | `default-src 'self'; script-src 'self'; ...` |
| `Referrer-Policy`           | `strict-origin-when-cross-origin`            |
| `Permissions-Policy`        | `camera=(), microphone=(), geolocation=()`   |

## Advisory Safety Chain

The advisory query endpoint applies a 13-step safety chain before returning a response:

1. **Input sanitisation** -- XSS prevention, null byte removal
2. **Rate limiting** -- Per-user throttle
3. **Query screening** -- Guardrails detect circumvention attempts and escalation triggers
4. **EATP genesis record** -- Trust anchor for the session
5. **Anti-amnesia injection** -- Constraint re-injection to prevent drift
6. **Domain detection** -- Classify which regulatory domains apply
7. **KB retrieval** -- Fetch relevant provisions via citation validator
8. **Response generation** -- KB-grounded response (production: Kaizen orchestrator)
9. **Confidence escalation check** -- Low confidence triggers red risk tier
10. **Response screening** -- Content validation of the generated response
11. **Disclaimer generation** -- Risk-tiered disclaimer (green/amber/red)
12. **Constraint envelope validation** -- Verify agent stayed within bounds
13. **Trust chain recording** -- Full attestation for audit trail

If any step blocks, the response is rejected with an appropriate message.

## Content Screening

### Query Screening (Guardrails)

Queries are screened for:

- Circumvention attempts (trying to bypass safety controls)
- Escalation triggers (queries requiring human specialist referral)

**Outcomes**: `PASS` (proceed), `BLOCK` (reject with explanation), `ESCALATE` (refer to human)

### Response Screening

Generated responses are screened before delivery. Blocked responses are replaced with a safe fallback message directing the user to a human specialist.

## PDPA Compliance

The `security/pdpa.py` module provides PDPA (Personal Data Protection Act) compliance utilities for handling personal data in accordance with Singapore regulations.

## Environment Variable Security

- All secrets loaded from `.env` (never hardcoded)
- `.env` excluded from git via `.gitignore`
- `.env.example` provided as a template (no real values)
- Production enforces non-default JWT secret and DEBUG=false
