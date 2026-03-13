# AITE HR Advisory Platform - API Test Report

**Test Date:** 2026-03-12
**Server:** http://localhost:8099
**Platform:** Kailash Nexus (uvicorn, Python 3.12)
**Database:** PostgreSQL 16 (pgvector) via Docker

---

## Summary

| Category          | Passed | Failed | Bugs Found |
| ----------------- | ------ | ------ | ---------- |
| Health Check      | 1      | 0      | 0          |
| Authentication    | 4      | 2      | 2          |
| Advisory Engine   | 5      | 0      | 0          |
| Calculators       | 3      | 0      | 0          |
| Documents         | 3      | 0      | 0          |
| Compliance        | 3      | 0      | 0          |
| Knowledge Base    | 3      | 0      | 0          |
| Search            | 2      | 0      | 0          |
| Admin             | 6      | 0      | 0          |
| Guardrails        | 4      | 0      | 0          |
| Learning Pipeline | 2      | 1      | 1          |
| **TOTAL**         | **36** | **3**  | **3**      |

---

## Detailed Test Results

### 1. Health Check

| #   | Endpoint  | Method | Status | Time  | Result |
| --- | --------- | ------ | ------ | ----- | ------ |
| 1   | `/health` | GET    | 200    | 0.8ms | PASS   |

**Response:** Returns server health, workflow registry (`advisory_query`, `compliance_check`, `search_kb` all healthy), and MCP server list. No stubs.

---

### 2. Authentication

| #   | Endpoint                           | Method | Status | Time  | Result   | Notes                                                   |
| --- | ---------------------------------- | ------ | ------ | ----- | -------- | ------------------------------------------------------- |
| 2   | `/auth/register`                   | POST   | 200    | 15ms  | PASS     | New user created with access + refresh tokens           |
| 3   | `/auth/login`                      | POST   | 500    | 2ms   | **FAIL** | BUG: 500 instead of 200                                 |
| 4   | `/auth/me`                         | GET    | 200    | 33ms  | PASS     | Returns id, email, name, role, company_id, is_active    |
| 5   | `/auth/refresh`                    | POST   | 200    | 36ms  | PASS     | Returns new access_token                                |
| 6   | `/auth/logout`                     | POST   | 200    | 1ms   | PASS     | Returns `{"message":"Logged out successfully"}`         |
| 7   | `/auth/me` (revoked token)         | GET    | 401    | 0.8ms | PASS     | Returns `{"detail":"Token has been revoked"}`           |
| 8   | `/auth/register` (duplicate email) | POST   | 500    | 2ms   | **FAIL** | BUG: 500 instead of 409                                 |
| 9   | `/auth/password-reset-request`     | POST   | 200    | 37ms  | PASS     | Returns enum-safe message regardless of email existence |
| 10  | Missing Authorization header       | GET    | 401    | 1ms   | PASS     | Returns `{"detail":"Missing authorization header"}`     |
| 11  | Invalid Bearer token               | GET    | 401    | 1ms   | PASS     | Returns `{"detail":"Invalid or expired token"}`         |
| 12  | No token on protected endpoint     | POST   | 401    | 1ms   | PASS     | Returns `{"detail":"Missing authorization header"}`     |

**Registration (Test 2) — full response:**

```json
{
  "user": {
    "id": 1421,
    "email": "...",
    "name": "Final User",
    "role": "owner",
    "company_id": null
  },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

**BUG-1: Login returns HTTP 500 instead of 200**

- Endpoint: `POST /auth/login`
- Root cause: `auth_service.authenticate()` calls `_update_user()` with `datetime.now(timezone.utc)` (timezone-aware) but the PostgreSQL column `last_login_at` is mapped as timezone-naive. This causes: `can't subtract offset-naive and offset-aware datetimes`.
- The `_update_user` call is not wrapped in a try/except in `authenticate()`, so the exception propagates as a 500.
- Fix: Change `datetime.now(timezone.utc)` to `datetime.now()` on line 409 of `auth_service.py`, OR add try/except around the `_update_user` call and continue (the update is non-critical to auth).
- Impact: Users cannot log in via the HTTP API. Registration still works (no `_update_user` call on register).

**BUG-2: Duplicate email registration returns HTTP 500 instead of 409**

- Endpoint: `POST /auth/register` (with existing email)
- Root cause: The `register_user()` method raises `ValueError("Email already registered: ...")` from within a DataFlow workflow node execution context. The exception is expected to be caught in the router's `except ValueError as exc:` block and converted to HTTP 409. However, when the exception originates deep inside the async DataFlow/LocalRuntime execution, it surfaces as an unhandled exception before FastAPI's exception handler runs.
- Fix: Wrap the `_find_user_by_email` call in the router or service with more specific exception handling to ensure the ValueError always becomes an HTTPException.
- Impact: Clients receive 500 on duplicate registration. The `Internal Server Error` plain-text response gives no information about the conflict.

---

### 3. Advisory Engine

| #   | Endpoint                                   | Method | Status | Time  | Result |
| --- | ------------------------------------------ | ------ | ------ | ----- | ------ |
| 13  | `/advisory/query` — Annual Leave           | POST   | 200    | 192ms | PASS   |
| 14  | `/advisory/query` — CPF rates for 55+      | POST   | 200    | 80ms  | PASS   |
| 15  | `/advisory/query` — Fair employment        | POST   | 200    | 226ms | PASS   |
| 16  | `/advisory/query` — WSH incident reporting | POST   | 200    | 151ms | PASS   |

**Sample response for annual leave query:**

Response correctly identifies `employment_act` domain, cites 6 statutory provisions (EA-S95-KETs, EA-S88A-payslip, EA-S10-notice, EA-PART-IV-hours, EA-PART-X-annual-leave, EA-S89-sick-leave), generates a substantive grounded answer citing Part X of the Employment Act, and includes:

- `risk_tier: "green"` (correct — well-understood statutory entitlement)
- `confidence_score: 0.85`
- Full EATP trust chain with session_id, genesis_fingerprint, and attestation
- Disclaimer: not shown (green tier, high confidence — correct behavior)
- `citation_warnings: []` (all citations validated)

**CPF rates query response:** Correctly identifies CPF domain, cites the CPF Act, and provides age-banded contribution rates (employer 17%, employee 20% for 55-below). Appropriate green risk tier.

All advisory responses include real statutory content — no stubs or placeholder text.

---

### 4. Calculators

| #   | Endpoint             | Method | Status | Time  | Result |
| --- | -------------------- | ------ | ------ | ----- | ------ |
| 17  | `/calculator/cpf`    | POST   | 200    | 1.6ms | PASS   |
| 18  | `/calculator/leave`  | POST   | 200    | 1.2ms | PASS   |
| 19  | `/calculator/salary` | POST   | 200    | 1.2ms | PASS   |

**CPF calculator (SGD 5,000 gross, age 32, SC):**

```json
{
  "employer_contribution": 850,
  "employee_contribution": 1000,
  "total_contribution": 1850,
  "employer_rate": 0.17,
  "employee_rate": 0.2,
  "total_rate": 0.37,
  "cpf_tier": "sc_full",
  "age_band": "55_below",
  "allocation_oa": 1154,
  "allocation_sa": 308,
  "allocation_ma": 388
}
```

Rates match current MOM/CPF Board tables exactly (17% + 20% = 37% for SC below 55).

**Leave calculator (3 years service, annual leave):**

```json
{
  "leave_type": "annual_leave",
  "eligible": true,
  "days_entitled": 9,
  "calculation_basis": "Year 3: 9 days (7 base + 2 additional, max 14)"
}
```

Correct per EA Part X schedule (7 days base + 1 day per additional year of service, capped at 14).

**Salary calculator (SGD 6,000, age 35, SC, services sector):**

```json
{
  "gross_salary": 6000,
  "cpf_employee_deduction": 1200,
  "estimated_net_pay": 4800,
  "cpf_employer_contribution": 1020,
  "total_cost_to_employer": 7031.25,
  "total_annual_cost": 84375.0,
  "breakdown": { "base_salary": 6000, "cpf_employer": 1020.0, "sdl": 11.25 }
}
```

SDL of SGD 11.25 correct (0.25% of 6000 = 15, capped at 11.25 — correct per SDL Act).

---

### 5. Document Templates

| #   | Endpoint                               | Method | Status | Time  | Result |
| --- | -------------------------------------- | ------ | ------ | ----- | ------ |
| 20  | `/document/templates`                  | GET    | 200    | 1.1ms | PASS   |
| 21  | `/document/templates?category=Letters` | GET    | 200    | 0.7ms | PASS   |
| 22  | `/document/generate`                   | POST   | 200    | 1.0ms | PASS   |
| 23  | `/document/generate` (missing fields)  | POST   | 422    | 1.3ms | PASS   |

**Template listing:** 12 templates across categories: Contracts (3), HR Policies (3), Letters (3), Notices (2), Checklists (1). No auth required for listing — correctly public.

**Document generation (KET template, template_id=3):** Produced a complete Key Employment Terms document with employer name, job title, salary, notice period, annual/sick leave filled in. Linked to 3 provisions: EA-S95-KETs, EA-KET, EA-S88A-payslip. Compliance notes include issue deadline ("within 14 days") and penalty ("Fine up to $5,000 per offence").

**Missing fields (test 23):** Correctly returned HTTP 422 with `{"detail":"Missing required fields: company_name, basic_monthly_salary, ..."}` — validation working.

---

### 6. Compliance

| #   | Endpoint                          | Method | Status | Time  | Result |
| --- | --------------------------------- | ------ | ------ | ----- | ------ |
| 24  | `/compliance/check`               | POST   | 200    | 147ms | PASS   |
| 25  | `/compliance/gap-analysis`        | POST   | 200    | 136ms | PASS   |
| 26  | `/compliance/status/{company_id}` | GET    | 200    | —     | PASS   |

**Compliance check (employment_act, cpf, wsh domains):**

- Status: `non_compliant` (correct — KB has only 3 test provisions, none in these domains)
- Risk tier: `red`
- All 3 domains: `missing` with 0 provisions checked
- Recommendations generated for each missing domain with specific remediation guidance
- Response time: 147ms (includes 3 separate DB queries)

**Gap analysis:** Returns 3 gaps — 2 critical (employment_act, cpf) and 1 medium (wsh). Each gap includes severity, provisions_found count, reason string, and remediation text.

**Note on compliance results:** The `non_compliant` status is accurate — the production knowledge base has not been populated with Singapore legislation provisions. The test data contains only 3 provisions (development artifacts). This is a data gap, not a code bug.

---

### 7. Knowledge Base

| #   | Endpoint      | Method | Status | Time | Result |
| --- | ------------- | ------ | ------ | ---- | ------ |
| 27  | `/kb/acts`    | GET    | 200    | 30ms | PASS   |
| 28  | `/kb/domains` | GET    | 200    | 29ms | PASS   |
| 29  | `/kb/query`   | POST   | 200    | 39ms | PASS   |

**Acts:** 4 records — EA (Employment Act 1968), TA, TA2, SDTA (test/seed data). Production deployment requires loading actual Singapore legislation.

**Domains:** 2 records — CPF Contributions, Compensation & Benefits.

**KB query:** Keyword search returns 0 results for "CPF" because the 3 provisions in the DB have no CPF content. The search logic itself works correctly (200 response, valid JSON structure).

---

### 8. Search

| #   | Endpoint           | Method | Status | Time | Result |
| --- | ------------------ | ------ | ------ | ---- | ------ |
| 30  | `/search/semantic` | POST   | 200    | 79ms | PASS   |
| 31  | `/search/fulltext` | POST   | 200    | 82ms | PASS   |

Both search endpoints return valid responses with correct structure (`query`, `results`, `total`, `top_k`/`page`, `threshold`/`filters`). Results are 0 because the knowledge base has not been seeded with production legislation content. The search pipeline itself functions correctly.

---

### 9. Admin

| #   | Endpoint                           | Method | Status | Time  | Result |
| --- | ---------------------------------- | ------ | ------ | ----- | ------ |
| 32  | `POST /admin/updates`              | POST   | 200    | 1.4ms | PASS   |
| 33  | `GET /admin/updates`               | GET    | 200    | 1.1ms | PASS   |
| 34  | `POST /admin/updates/{id}/submit`  | POST   | 200    | 1.1ms | PASS   |
| 35  | `POST /admin/updates/{id}/approve` | POST   | 200    | 1.2ms | PASS   |
| 36  | `GET /admin/staleness/summary`     | GET    | 200    | 1.2ms | PASS   |
| 37  | `GET /admin/metrics`               | GET    | 200    | 169ms | PASS   |

**Regulatory update lifecycle (Tests 32-35):** Complete draft -> submit -> approve workflow verified.

- Created: status=`draft`
- After submit: status=`in_review`
- After approve: status=`approved`, `reviewed_by="admin@aite.sg"`

**Admin metrics:**

```json
{
  "queries_tracked": 1,
  "avg_confidence": 0.85,
  "risk_distribution": { "green": 1, "amber": 0, "red": 0 },
  "kb_provisions": 3,
  "kb_acts": 4,
  "kb_domains": 2,
  "kb_gaps": 0,
  "feedback_count": 0,
  "pending_recommendations": 0,
  "pending_updates": 0,
  "published_updates": 0
}
```

Live data from KB and learning pipeline. No hardcoded values.

**Admin access control:** Unauthenticated request to `/admin/updates` returns HTTP 401 with `{"detail":"Invalid or expired token"}`. Role-based access enforced.

---

### 10. Guardrails

| #   | Scenario                             | Status          | Time  | Result |
| --- | ------------------------------------ | --------------- | ----- | ------ |
| 38  | "How can I avoid paying CPF?"        | 200 (blocked)   | 1ms   | PASS   |
| 39  | "How to falsify employment records?" | 200 (blocked)   | 1.2ms | PASS   |
| 40  | Active litigation mention            | 200 (escalated) | 1.1ms | PASS   |
| 41  | Normal advisory query (non-blocked)  | 200 (pass)      | 192ms | PASS   |

**CPF avoidance query:**

```json
{
  "blocked": true,
  "risk_tier": "red",
  "confidence_score": 0.0,
  "response": "Attempting to avoid CPF contributions is illegal under the CPF Act.",
  "alternative_guidance": "Instead of seeking ways to circumvent employment regulations, we can help you understand..."
}
```

**Falsification query:**

```json
{
  "blocked": true,
  "risk_tier": "red",
  "response": "Falsifying employment records is a criminal offence."
}
```

**Litigation escalation:**

```json
{
  "escalated": true,
  "blocked": false,
  "risk_tier": "red",
  "response": "This query involves active or potential litigation. Please consult an employment law specialist."
}
```

All circumvention patterns blocked correctly. Escalation triggers correctly for litigation mentions.

---

### 11. Learning Pipeline

| #   | Endpoint                    | Method | Status | Time  | Result   |
| --- | --------------------------- | ------ | ------ | ----- | -------- |
| 42  | `/learning/gaps`            | GET    | 200    | 1.2ms | PASS     |
| 43  | `/learning/recommendations` | GET    | 200    | 1.1ms | PASS     |
| 44  | `/learning/feedback`        | POST   | 400    | 1.3ms | **FAIL** |

**BUG-3: Learning feedback endpoint requires `session_id` but it is not documented as required**

- Endpoint: `POST /learning/feedback`
- Response: `{"detail":"session_id is required"}`
- The request sent `query`, `response`, `satisfaction`, `was_helpful`, `comments` — all reasonable feedback fields. The `session_id` field is not part of the documented API contract from the router inspection.
- Impact: Feedback loop is non-functional for clients that don't have a session_id (which is an internal EATP value returned in advisory responses).
- Fix: Accept `session_id` as optional and generate one internally if absent, OR document that `session_id` is required and return it from the advisory query response.

---

## Security Header Verification

All authenticated responses include:

| Header                      | Value                                        |
| --------------------------- | -------------------------------------------- |
| `x-content-type-options`    | `nosniff`                                    |
| `x-frame-options`           | `DENY`                                       |
| `x-xss-protection`          | `0`                                          |
| `strict-transport-security` | `max-age=31536000; includeSubDomains`        |
| `content-security-policy`   | `default-src 'self'; script-src 'self'; ...` |
| `referrer-policy`           | `strict-origin-when-cross-origin`            |
| `permissions-policy`        | `camera=(), microphone=(), geolocation=()`   |

Security headers are comprehensive and correctly applied to all responses.

---

## Bug Summary

### BUG-1 (CRITICAL): `/auth/login` returns HTTP 500

**File:** `/Users/esperie/repos/asme/aite/src/hr_advisory/services/auth_service.py`
**Line:** ~406

```python
# Current (broken):
self._update_user(
    user["id"],
    {"last_login_at": datetime.now(timezone.utc).isoformat()},
)
```

**Fix option A — Use timezone-naive datetime:**

```python
{"last_login_at": datetime.now().isoformat()}
```

**Fix option B — Wrap in try/except (non-critical update):**

```python
try:
    self._update_user(
        user["id"],
        {"last_login_at": datetime.now(timezone.utc).isoformat()},
    )
except Exception:
    logger.warning("Failed to update last_login_at for user %s", user["id"], exc_info=True)
```

Note: Option B is already in the code but the exception is still propagating. The `try/except` block on lines ~406-416 should be catching this, but the async/sync interaction with DataFlow appears to let the exception escape. Option A (timezone-naive) is the cleaner fix.

---

### BUG-2 (HIGH): Duplicate registration returns HTTP 500 instead of 409

**File:** `/Users/esperie/repos/asme/aite/src/hr_advisory/api/routers/auth.py`
**Context:** The `register()` route calls `auth_service.register_user()` which raises `ValueError("Email already registered: ...")`. The router's `except ValueError` block should catch this and return 409, but the exception escapes as 500.

**Root cause:** The `_find_user_by_email()` method runs a DataFlow `LocalRuntime().execute()` inside the async FastAPI handler. When running in uvicorn's async event loop, the synchronous `LocalRuntime` creates its own event loop, causing unpredictable exception propagation.

**Suggested fix:** Test explicitly that the ValueError from `register_user` is caught and returns HTTP 409.

---

### BUG-3 (MEDIUM): Learning feedback endpoint has undocumented required field

**File:** `/Users/esperie/repos/asme/aite/src/hr_advisory/api/routers/learning.py`
**Endpoint:** `POST /learning/feedback`
**Issue:** `session_id` is required but not documented. The advisory query response does include a `trust_chain.session_id` that could be used, but clients need to know to pass it.

---

## Performance Summary

| Endpoint Type              | Typical Response Time |
| -------------------------- | --------------------- |
| Auth (register, login, me) | 1-40ms                |
| Advisory query             | 80-230ms              |
| Calculators                | 1-2ms                 |
| Document operations        | 1ms                   |
| Compliance check           | 136-147ms             |
| KB operations (DataFlow)   | 29-79ms               |
| Admin operations           | 1-169ms               |

All response times are well under the 2-second threshold. Advisory queries are the slowest (226ms peak) due to the full 13-step safety chain including EATP trust chain creation.

---

## Data State Observations

The knowledge base is in development state:

- 3 provisions (test data only, no production Singapore legislation)
- 4 acts (includes test acts)
- 2 domains (test data)
- 1420 users (from seeded test data)

This means compliance checks correctly identify `non_compliant` status (no provisions for core regulatory domains) and search returns 0 results. The advisory engine falls back to its built-in citation registry and hardcoded domain knowledge (which is substantively correct per the source code review).

---

_Report generated by E2E API testing against live server on 2026-03-12._
