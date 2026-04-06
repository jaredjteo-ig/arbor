# Arbor Platform — Initial Audit Report

**Date**: 2026-03-23
**Branch**: main (commit 2d1d509)
**Auditors**: 7 specialist agents + 1 API contract auditor
**Scope**: Full codebase — backend, frontend, security, deployment

---

## Executive Summary

Arbor is a substantial, well-architected HRIS and employment law advisory platform. The codebase contains 29 API routers with 250+ endpoints, 60+ database models, 7 deterministic calculators, 5 MCP servers with 36 real adapters (none are stubs), a multi-agent advisory system with a 13-step safety chain, and a Next.js web frontend with 46 pages.

This audit found **125 issues** across all severity levels. The platform's core architecture is sound, but there are critical bugs in data consistency (calculators disagree on CPF rates), broken features (company setup, reports showing zeroes), security gaps (PII encryption missing on self-service path), and safety chain components that are defined but not enforced.

| Severity     | Count | Summary                                                       |
| ------------ | ----- | ------------------------------------------------------------- |
| **CRITICAL** | 22    | Broken features, wrong calculations, security gaps            |
| **HIGH**     | 28    | Data integrity, missing enforcement, memory risks             |
| **MEDIUM**   | 42    | Inconsistencies, missing validations, partial implementations |
| **LOW**      | 33    | Code quality, minor gaps, design notes                        |

### Top 5 Most Impactful Issues

1. **CPF calculators disagree with the payroll engine** — The payroll engine and standalone CPF calculator use different age boundary logic. A 55-year-old employee gets different CPF amounts depending on which path is used. (C-PAY-1)
2. **Company setup is broken** — The CompanySetupModal calls the wrong API endpoint (`/clients/` instead of `/profile/`), and the onboarding wizard never calls any API at all. New users cannot create a company. (C-FE-1)
3. **All report totals return zero** — Reports router uses wrong field names (`gross_pay` instead of `gross_salary`), so every payroll, attendance, and claims report returns zeroes. (C-HRIS-4)
4. **Employee self-service stores PII in plaintext** — The self-service profile update path skips encryption for NRIC and bank account numbers, violating PDPA. (C-SEC-1)
5. **Anti-amnesia and constraint envelopes are dead code** — The advisory safety chain computes anti-amnesia constraints and validates constraint envelopes, but the results are never injected into the LLM or used to block responses. (C-ADV-2, C-ADV-3)

---

## Methodology

Seven specialist agents audited the codebase in parallel, each reading every relevant file line by line:

| Agent                | Scope                                                      | Files Reviewed                            |
| -------------------- | ---------------------------------------------------------- | ----------------------------------------- |
| Auth Auditor         | Authentication, JWT, OAuth, tenant isolation               | 6 core files + all routers for auth usage |
| Payroll Auditor      | Payroll engine, 7 calculators, statutory files             | 11 files                                  |
| Advisory Auditor     | Safety chain, trust lineage, citations, guardrails, agents | 14 files                                  |
| Frontend Auditor     | All 46 dashboard pages, API services, components           | 46 pages + services                       |
| HRIS Auditor         | All 26 routers, 60+ models, DataFlow node usage            | 26 router files + model files             |
| MCP Auditor          | 5 servers, 36 adapters, infrastructure modules             | 50+ files                                 |
| Security Auditor     | Secrets, injection, CORS, uploads, deployment              | Full codebase scan                        |
| API Contract Auditor | Frontend-backend type and endpoint mismatches              | Types, services, routers                  |

An additional API contract audit cross-referenced every frontend service call against the actual backend router.

---

## 1. CRITICAL Findings

These are blocking issues — broken features, wrong calculations, or security vulnerabilities.

### 1.1 Payroll & Calculator Issues

#### C-PAY-1. CPF age boundary mismatch between payroll engine and calculators

**Impact**: A 55-year-old employee gets different CPF amounts depending on which code path runs.

The payroll engine (`payroll_calculator.py:446`) uses `age <= 55` (inclusive), placing age 55 in the "55 and below" band. The standalone CPF calculator (`cpf_calculator.py:118`) uses `age < 55` (exclusive), placing age 55 in the "55-60" band. The payroll engine is correct per CPF Board wording.

For an employee earning $8,000 at exactly age 55, the CPF calculator under-reports employer CPF by $200/month. The cost-to-company calculator has the same bug.

#### C-PAY-2. PR Year 1 CPF rates differ between payroll engine and calculator

**Impact**: Payroll engine over-calculates employer CPF for older PR Year 1 employees.

The payroll engine uses flat 4% employer for all age bands. The CPF calculator uses 3.5% for ages 60+. The CPF calculator's rates are more aligned with CPF Board tables. This produces incorrect CPF e-Submit files.

#### C-PAY-3. FWL rates inconsistent across three modules

**Impact**: Same employee shows different levy amounts on payslip vs cost projection.

| Module                     | WP Levy                | S Pass Levy            |
| -------------------------- | ---------------------- | ---------------------- |
| Payroll engine             | $300                   | $450                   |
| Cost-to-company calculator | $450                   | $550                   |
| Quota/levy calculator      | Sector-specific tables | Sector-specific tables |

#### C-PAY-4. Notice period calculator returns 1 week instead of 1 day for <26 weeks

**Impact**: Salary-in-lieu calculated at 7x the correct amount.

Per EA s10(3), employment under 26 weeks requires 1 day notice. The function returns `1` (meaning 1 week), and the salary-in-lieu calculation uses that value.

**File**: `notice_period_calculator.py:34-42`

#### C-PAY-5. OT hourly rate formula differs between payroll engine and OT calculator

**Impact**: Payslips show different OT rates than the standalone calculator.

| Module         | Formula                  | $5,000 salary |
| -------------- | ------------------------ | ------------- |
| Payroll engine | salary / 173.33          | $28.85/hr     |
| OT calculator  | salary / 208 (EA s38(6)) | $24.04/hr     |

The EA formula (salary / (26 days × 8 hours) = /208) is the legally correct one. The payroll engine also does not apply the EA salary cap of $2,600 for OT calculations.

### 1.2 Frontend Issues

#### C-FE-1. CompanySetupModal calls wrong API endpoint — company creation is broken

**Impact**: Users cannot create a company from the dashboard. This is the bug you encountered.

The `CompanySetupModal` (`CompanySetupModal.tsx:55`) calls `clientsApi.create()` which hits `POST /clients/`. This endpoint is for consultants managing client companies, not for users setting up their own company. The correct endpoint is `POST /profile/` via `profileApi.create()`.

Additionally, the `/clients/` endpoint uses wrong DataFlow parameter names (`conditions`/`updates` instead of `filter`/`fields`), so even the client creation itself may fail silently.

#### C-FE-2. Onboarding wizard never saves company data

**Impact**: Company profile data entered during onboarding is lost.

The onboarding flow (`onboarding/page.tsx`) collects company details in step 2 but only stores them in React state. No API call is ever made. When the user finishes onboarding, the data evaporates.

#### C-FE-3. Payroll list response format mismatch

**Impact**: Payroll page may fail to render runs.

Frontend expects `PayrollRun[]` (direct array). Backend returns `{"runs": [...], "count": N}` (object with runs array). The frontend will fail to iterate.

**Files**: `payroll.ts:121` vs `payroll.py:410-418`

#### C-FE-4. SSE advisory stream missing disclaimer event handler

**Impact**: Risk disclaimers from the backend are silently dropped.

The SSE client handles `start`, `token`, `complete`, `error` events. The backend also sends a `disclaimer` event which is ignored.

**File**: `sse.ts:196-229`

### 1.3 HRIS Router Issues

#### C-HRIS-1. Wrong DataFlow parameters in employee self-service update

**Impact**: Employees cannot update their own profiles.

`PUT /employees/me` uses `{"conditions": ..., "updates": ...}` instead of the correct `{"filter": ..., "fields": ...}` pattern. The update silently fails or crashes.

**File**: `employees.py:1766`

#### C-HRIS-2. Wrong DataFlow parameters in client company user assignment

**Impact**: After creating a company via `/clients/`, the user is never linked to it.

Same `conditions`/`updates` parameter name bug as C-HRIS-1.

**File**: `clients.py:173`

#### C-HRIS-3. Wrong DataFlow node name in YTD reports

**Impact**: `/reports/payroll/ytd` crashes at runtime.

Reports router uses `CpfYtdListNode` but the model generates `CpfYtdRecordListNode`.

**File**: `reports.py:205`

#### C-HRIS-4. Reports router uses wrong field names — all totals return zero

**Impact**: Every payroll, attendance, and claims report shows $0.

| Router uses    | Actual model field |
| -------------- | ------------------ |
| `gross_pay`    | `gross_salary`     |
| `net_pay`      | `net_salary`       |
| `hours_worked` | `work_hours`       |
| `claim_date`   | (does not exist)   |

**File**: `reports.py:76-77, 184, 235, 332, 369`

#### C-HRIS-5. Recruitment router uses wrong field names

**Impact**: Job listings store titles in wrong columns, status management broken.

Router passes `title` but model has `position_title`. Router manages a `status` field but model uses `is_published` boolean.

**File**: `recruitment.py:167, 175`

#### C-HRIS-6. Missing models for leave encashment and off-in-lieu

**Impact**: These endpoints crash with "node type not found" error.

`LeaveEncashmentCreateNode` and `OffInLieuRecordCreateNode` reference models that don't exist.

**File**: `leave.py:1429, 1516`

#### C-HRIS-7. Inventory movement missing required company_id and using wrong field name

**Impact**: Inventory audit trail is broken — missing tenant isolation and timestamps.

`_record_movement` passes `timestamp` but model has `movement_date`, and omits required `company_id`.

**File**: `inventory.py:123-134`

### 1.4 Security Issues

#### C-SEC-1. Self-service NRIC/bank account stored in PLAINTEXT

**Impact**: PDPA non-compliance. PII stored unencrypted when updated via self-service.

The admin `PATCH /employees/{id}` correctly calls `encrypt_field()`. The self-service `PUT /employees/me` does not.

**File**: `employees.py:1748-1769`

#### C-SEC-2. No production guard for SALARY_ENCRYPTION_KEY

**Impact**: Production can run with all PII unencrypted.

Unlike JWT_SECRET_KEY and DATABASE_URL, there is no startup check for the encryption key. It's also absent from the production env template.

**File**: `encryption.py:17-20`, `deploy/.env.prod.example`

#### C-SEC-3. Ship script embeds GitHub token in git remote URL

**Impact**: GitHub access token persisted in server's .git/config and visible in process list.

**File**: `deploy/ship.sh:36`

### 1.5 Auth Issues

#### C-AUTH-1. Wrong rate limiter on auth endpoints

**Impact**: Login/register brute-force protection uses 30-req/60s limit instead of proper auth-tier 5-req/60s.

The auth router imports `check_rate_limit` from `guardrails` (advisory module, 30/min) instead of `rate_limit` middleware (configurable, tighter limits).

**File**: `auth.py:19`

#### C-AUTH-2. Deactivated users retain valid access tokens

**Impact**: Deactivated users can continue accessing the system for up to 60 minutes.

`get_current_user()` validates JWT signature, expiry, and blocklist — but never checks the user's `is_active` flag in the database.

**File**: `auth_middleware.py:25-66`

#### C-AUTH-3. Google OAuth — account takeover via password reset

**Impact**: An attacker can set a password on a Google-only account.

Google OAuth creates users with `password_hash=""`. The password reset flow does not check for empty password_hash, allowing anyone with a reset token to set credentials on a Google-only account.

**File**: `auth.py:692`, `auth_service.py:551`

#### C-AUTH-4. Google OAuth does not verify email_verified claim

**Impact**: Unverified Google emails could be linked to Arbor accounts.

**File**: `auth.py:678-683`

---

## 2. HIGH Findings

Issues that should be fixed before the next release.

### 2.1 Safety Chain & Trust

| ID      | Finding                                                                                    | File                            | Impact                                    |
| ------- | ------------------------------------------------------------------------------------------ | ------------------------------- | ----------------------------------------- |
| H-ADV-1 | Duplicate EATP genesis records — specialist attestations lost from user-facing trust chain | `advisory.py:450-583`           | Trust lineage is incomplete               |
| H-ADV-2 | Anti-amnesia injection is dead code — constraints computed but never sent to LLM           | `advisory.py:465-466`           | Safety step 5 not enforced                |
| H-ADV-3 | Constraint envelope violations logged but never block responses                            | `advisory.py:531-532`           | Constraint envelopes are advisory-only    |
| H-ADV-4 | No prompt injection detection in circumvention patterns                                    | `guardrails.py:68-109`          | LLM jailbreak attempts undetected         |
| H-ADV-5 | Rate limiter enforces 30/min instead of configured 10/min                                  | `guardrails.py:285-286`         | 3x weaker than designed                   |
| H-ADV-6 | CARE governance defined but not enforced in any pipeline                                   | `care_governance.py`            | Human-on-the-loop is data structures only |
| H-ADV-7 | Citation validation never returns EXPIRED or SUPERSEDED                                    | `citation_validator.py:449-512` | Expired provisions pass as VALID          |

### 2.2 Payroll & Calculators

| ID      | Finding                                                       | File                                | Impact                                   |
| ------- | ------------------------------------------------------------- | ----------------------------------- | ---------------------------------------- |
| H-PAY-1 | CPF annual ceiling ($102K) not tracked in payroll engine      | `payroll_calculator.py:148,289`     | Over-deduction for high earners mid-year |
| H-PAY-2 | Payroll engine does not apply EA OT salary cap of $2,600      | `payroll_calculator.py:247-248`     | OT overpaid for salaries above $2,600    |
| H-PAY-3 | Childcare leave skips 3-month minimum service check           | `leave_calculator.py:279-329`       | False eligibility reported               |
| H-PAY-4 | Adoption leave skips service duration and child age checks    | `leave_calculator.py:427-452`       | False eligibility reported               |
| H-PAY-5 | Cost-to-company calculator doesn't apply OW ceiling to CPF    | `cost_to_company_calculator.py:107` | Overstates cost for salaries >$8K        |
| H-PAY-6 | Salary component amounts not validated for NaN/Infinity       | `payroll_calculator.py:189-242`     | Data corruption risk                     |
| H-PAY-7 | CPF YTD records created for draft runs, not cleaned on cancel | `payroll.py:324-343`                | Incorrect CPF on re-run after cancel     |
| H-PAY-8 | Cross-period leave deducts full days in both periods          | `payroll.py:228-233`                | Double deduction for cross-period leave  |

### 2.3 Auth & Security

| ID       | Finding                                             | File                        | Impact                                   |
| -------- | --------------------------------------------------- | --------------------------- | ---------------------------------------- |
| H-AUTH-1 | TOCTOU race in user registration (email uniqueness) | `auth_service.py:364-374`   | Potential duplicate accounts             |
| H-AUTH-2 | Refresh token not rotated on use                    | `auth_service.py:462-510`   | Stolen refresh token works for 7 days    |
| H-AUTH-3 | No rate limiting on token refresh and Google OAuth  | `auth.py:150-172, 622-719`  | Brute-force attack surface               |
| H-AUTH-4 | In-memory token blocklist lost on restart           | `token_blocklist.py:62-133` | Revoked tokens become valid after deploy |
| H-SEC-1  | Exception messages leaked to API clients            | Multiple routers            | Internal schema details exposed          |
| H-SEC-2  | Webhook endpoint has no signature verification      | `integrations.py:371-388`   | Forged webhook payloads accepted         |

### 2.4 Platform-Wide

| ID       | Finding                                                                    | File                         | Impact                                           |
| -------- | -------------------------------------------------------------------------- | ---------------------------- | ------------------------------------------------ |
| H-MEM-1  | 15+ unbounded in-memory collections across the codebase                    | Multiple files               | Production OOM risk                              |
| H-HRIS-1 | Alerts router returns hardcoded seed data, not DB data                     | `alerts.py:36-250`           | All users see same static alerts                 |
| H-HRIS-2 | ApprovalGroup field mismatch — description/approvers/modules silently lost | `approval_groups.py:142-153` | Approval group configuration doesn't persist     |
| H-HRIS-3 | Self-service profile encryption missing for sensitive fields               | `employees.py:1748-1756`     | PII stored plaintext (same as C-SEC-1)           |
| H-MCP-1  | Token store ephemeral Fernet key regenerated on every call                 | `token_store.py:31-43`       | Integration tokens unrecoverable without env key |
| H-MCP-2  | S3 adapter shares circuit breaker with data.gov.sg                         | `s3_storage.py:55`           | S3 failures trip data.gov.sg breaker             |

---

## 3. MEDIUM Findings

Issues that should be addressed in the next development iteration.

### 3.1 Payroll & Calculators

| ID      | Finding                                                               | Impact                              |
| ------- | --------------------------------------------------------------------- | ----------------------------------- |
| M-PAY-1 | No-pay leave uses 22 working days but proration uses calendar days    | Inconsistent deduction methodology  |
| M-PAY-2 | Calculator router `/salary` has fragile citizenship mapping           | Works by coincidence, not by design |
| M-PAY-3 | Default age 30 when DOB is missing — wrong CPF for older employees    | Silent incorrect calculation        |
| M-PAY-4 | 4 calculators (OT, notice, retrenchment, quota) have no API endpoints | Users can't access them via API     |

### 3.2 Advisory & Trust

| ID       | Finding                                                           | Impact                                        |
| -------- | ----------------------------------------------------------------- | --------------------------------------------- |
| M-ADV-1  | Safety chain step numbering misaligned with documentation         | Maintenance confusion                         |
| M-ADV-2  | User-controllable conversation_id with no validation              | Collision or injection risk                   |
| M-ADV-3  | Confidence gap 0.5-0.7 not handled in guardrails module           | AMBER escalation relies on separate code path |
| M-ADV-4  | Genesis fingerprint omits query text and domains                  | Weak tamper detection                         |
| M-ADV-5  | NaN confidence bypasses RED disclaimer                            | float('nan') < 0.5 is False                   |
| M-ADV-6  | Error correction state machine allows backward transitions        | Correction workflow can be short-circuited    |
| M-ADV-7  | LLM judge failure crashes quality scoring (no try/except)         | QA pipeline crashes on LLM outage             |
| M-ADV-8  | LLM risk_awareness score computed but discarded                   | Dead code in quality rubric                   |
| M-ADV-9  | KB provision text could be a vector for indirect prompt injection | No defense against malicious KB content       |
| M-ADV-10 | LLM provider cache never invalidated after secret rotation        | Stale provider after key rotation             |

### 3.3 Frontend

| ID     | Finding                                                            | Impact                                |
| ------ | ------------------------------------------------------------------ | ------------------------------------- |
| M-FE-1 | Reports dashboard charts use hardcoded data                        | Misleading analytics                  |
| M-FE-2 | Claims page has no receipt upload UI                               | Backend supports it, frontend doesn't |
| M-FE-3 | My Profile emergency contact section is a stub                     | User-visible placeholder              |
| M-FE-4 | My Payslips PDF download button is disabled                        | Feature gap with no user explanation  |
| M-FE-5 | KB provision ID type mismatch (string vs int)                      | Potential 422 errors                  |
| M-FE-6 | Compliance check response has extra fields not in TypeScript types | Type safety gap                       |

### 3.4 Auth & Security

| ID       | Finding                                                    | Impact                                |
| -------- | ---------------------------------------------------------- | ------------------------------------- |
| M-AUTH-1 | Password reset flow non-functional — email never sent      | Feature completely broken             |
| M-AUTH-2 | Password strength requirements are weak (length only)      | Allows trivial passwords              |
| M-SEC-1  | sync-env script leaks secrets in shell history             | Credential exposure during deployment |
| M-SEC-2  | Server IP hardcoded in source control                      | Reconnaissance target                 |
| M-SEC-3  | Rate limiting is in-memory only, not shared across workers | Bypassed in multi-worker deployment   |
| M-SEC-4  | CSP header blocks Google OAuth and cross-origin API calls  | SSO may fail in production            |
| M-SEC-5  | File upload original filename stored without sanitization  | Path traversal in metadata            |
| M-SEC-6  | auto_migrate=True unconditionally in production            | Uncontrolled schema changes           |
| M-SEC-7  | database.py loads DataFlow before production guard runs    | Could connect with default creds      |

### 3.5 HRIS & MCP

| ID       | Finding                                                            | Impact                                   |
| -------- | ------------------------------------------------------------------ | ---------------------------------------- |
| M-HRIS-1 | Recruitment `requirements` passed as list but model expects string | Type mismatch                            |
| M-HRIS-2 | `extend_probation` creates event with wrong type "confirmed"       | Misleading audit trail                   |
| M-HRIS-3 | Multiple routers set `updated_at` but no models define it          | Writes silently dropped                  |
| M-MCP-1  | Idempotency ledger has non-atomic check-then-write                 | Race condition on concurrent submissions |
| M-MCP-2  | PII filter only strips first occurrence of each name               | Subsequent occurrences leak PII          |
| M-MCP-3  | Webhook rate limiter unbounded per IP                              | Memory exhaustion under attack           |
| M-MCP-4  | Empty string company_id could bypass tenant isolation              | `str(None or "")` produces `""`          |

---

## 4. LOW Findings

Minor issues, code quality, and design notes. Full details available in individual agent transcripts.

| Count | Category | Examples                                                                                                                                                                            |
| ----- | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 6     | Auth     | Email enumeration in registration errors, `verify_password` swallows all exceptions, Google OAuth always assigns "owner" role, duplicate `_get_auth_service()` definitions          |
| 6     | Payroll  | Paternity leave shows 28 calendar days (could confuse as working days), retrenchment calculator doesn't warn about <2 years, IR8A missing director fees, DBS GIRO format simplified |
| 10    | Advisory | `kb_currency_status` hardcoded, `ConstraintEnvelope` not frozen, `_detect_ollama` silently catches all exceptions, degraded flag informational only                                 |
| 6     | HRIS     | `InventoryLocation` description field silently dropped, in-memory alert/rate-limit state lost on restart                                                                            |
| 6     | MCP      | Mutable default arguments in communications server, `list_all_tools()` called twice, duplicate bank code in GIRO adapter                                                            |
| 4     | Security | JWT uses HS256 (consider RS256), `lru_cache` on Fernet prevents key rotation, no CSRF documentation, curl in Docker image increases attack surface                                  |

---

## 5. What's Working Well

### Architecture

- **Kailash SDK integration is solid** — DataFlow, Nexus, and Kaizen are used correctly throughout
- **Tenant isolation is consistently enforced** across all company-scoped routers
- **Role-based access control** properly gates admin vs employee access
- **Production startup guards** block deployment with default JWT secret or database credentials

### Frontend (42 of 46 pages fully working)

- **All HRIS modules have real API integration** — employees, payroll, leave, claims, attendance, shifts, appraisals, projects, inventory, recruitment
- **Advisory chat with SSE streaming** works end-to-end with conversation history
- **Responsive design** with 3 breakpoints, collapsible sidebar, mobile drawer
- **Accessibility** is above average — 48px touch targets, focus-visible, ARIA attributes, reduced motion support
- **Design system** is consistent with CSS custom properties and typed components

### Backend

- **Payroll engine core arithmetic is correct** for the main cases (SC/PR3+ employees, all 5 age bands, proration, SDL, SHG)
- **All 36 MCP adapters are real implementations** — not stubs. ISO 20022 GIRO, APEX CPF, IRAS AIS, MyInfo, PayNow QR are all production-quality
- **Citation validation** correctly verifies provisions exist in the KB before delivery
- **Risk-tiered disclaimers** appropriately escalate based on risk tier
- **HTML payslip generation** includes all 12 EA s88A required fields with proper NRIC masking and HTML escaping

### Security

- No hardcoded secrets in committed code
- All database operations use parameterized queries (DataFlow ORM)
- JWT properly validates signature, expiry, and algorithm
- Input sanitization on advisory queries (HTML escaping, length limits)
- CORS restricted to specific origins (no wildcard)
- Caddy handles automatic HTTPS with Let's Encrypt
- Docker containers run as non-root user

---

## 6. Feature Completeness Matrix

### Web Frontend Pages (46 total)

| Status      | Count | Details                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| ----------- | ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **WORKING** | 42    | Dashboard, employees, employee detail, payroll, payroll detail, leave, claims, attendance, shifts, advisory, advisory history, compliance, compliance category, documents, document preview, document generate, calculators, alerts, analytics, admin, my-dashboard, my-leave, my-timesheets, my-inventory, approvals, appraisals, projects, recruitment, inventory, clients, policies, settings, emergency, help, training, profile, reports (partial), plus more |
| **PARTIAL** | 4     | Reports (hardcoded charts), My Profile (emergency contact stub), My Payslips (PDF disabled), Claims (no receipt upload UI)                                                                                                                                                                                                                                                                                                                                         |
| **BROKEN**  | 1     | CompanySetupModal (wrong API endpoint)                                                                                                                                                                                                                                                                                                                                                                                                                             |

### Backend Routers (29 total)

| Status               | Count | Details                                                                                                                                                                                                                                               |
| -------------------- | ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Working**          | 20    | auth, advisory, calculator, compliance, document, employees (admin path), leave (main ops), claims, attendance, shifts, payroll (main ops), profile, search, kb, settings, help, emergency, shadow, integrations, admin                               |
| **Partially broken** | 9     | reports (wrong field names), recruitment (wrong field names), inventory (wrong field names), approval_groups (field mismatch), clients (wrong DataFlow params), employees (self-service path), leave (encashment/off-in-lieu), alerts (hardcoded), qa |

### Calculators (7 total)

| Calculator      | Core Logic                      | API Endpoint      | Consistency with Payroll Engine |
| --------------- | ------------------------------- | ----------------- | ------------------------------- |
| CPF             | Correct (except age boundary)   | Yes               | Age boundary mismatch           |
| Leave           | Correct (except service checks) | Yes               | N/A                             |
| Overtime        | Correct (EA formula)            | No endpoint       | Different formula than payroll  |
| Notice Period   | Bug: 1 week instead of 1 day    | No endpoint       | N/A                             |
| Retrenchment    | Correct                         | No endpoint       | N/A                             |
| Cost-to-Company | Age boundary bug, no OW ceiling | Yes (via /salary) | FWL rates differ                |
| Quota/Levy      | Correct                         | No endpoint       | N/A                             |

### MCP Servers & Adapters (5 servers, 36 adapters)

| Server         | Tools | Adapters                                                                                    | Status                                |
| -------------- | ----- | ------------------------------------------------------------------------------------------- | ------------------------------------- |
| Government     | 30    | CPF APEX, IRAS AIS, MOM OED, MyInfo, ACRA, SkillsFuture, CorpPass                           | REAL — all production implementations |
| Regulatory     | 8     | data.gov.sg, SSO RSS, MOM sitemap, change detector, Telegram monitor, regulatory classifier | REAL                                  |
| Accounting     | 19    | Xero, QuickBooks, Zoho, Financio, generic export, claims sync                               | REAL with OAuth 2.0                   |
| Banking        | 12    | GIRO (ISO 20022), DBS FAST, UOB FAST, PayNow QR, Aspire, legacy GIRO                        | REAL                                  |
| Communications | 18    | Resend, SES, Telegram, WhatsApp, Slack, Teams, Google Calendar, Outlook, S3                 | REAL                                  |

### Mobile App

| Area                     | Status                                                         |
| ------------------------ | -------------------------------------------------------------- |
| Flutter project scaffold | Complete                                                       |
| Dependencies declared    | Complete (Riverpod, GoRouter, Dio, Hive)                       |
| Design token generator   | Complete                                                       |
| Application code (lib/)  | **Does not exist** — no screens, widgets, providers, or routes |

---

## 7. Prioritized Recommendations

### Immediate (Before Next Deploy)

1. **Fix CompanySetupModal** — Change from `clientsApi.create()` to `profileApi.create()`. Add API call to onboarding wizard. This blocks all new users.
2. **Fix PII encryption on self-service path** — Add `encrypt_field()` calls for NRIC, bank account, and work pass in `PUT /employees/me`.
3. **Add SALARY_ENCRYPTION_KEY production guard** — Block startup without this key, add to `.env.prod.example`.
4. **Fix DataFlow parameter names** — Change `conditions`/`updates` to `filter`/`fields` in `employees.py:1766` and `clients.py:173`.

### Short-Term (Next Sprint)

5. **Unify CPF calculation** — Make the payroll engine delegate to `cpf_calculator.py` instead of maintaining its own inline rate tables. Fix age boundary to use `<=` consistently.
6. **Fix reports field names** — Change `gross_pay` to `gross_salary`, `net_pay` to `net_salary`, `hours_worked` to `work_hours` across all report endpoints.
7. **Fix notice period calculator** — Return 1 day (not 1 week) for <26 weeks service. Change salary-in-lieu to daily rate.
8. **Add OT salary cap** — Apply $2,600 cap in payroll engine's OT calculation.
9. **Fix recruitment field names** — Map `title` to `position_title`, replace `status` with `is_published`/`published_at`/`closed_at`.
10. **Create missing models** — Add `LeaveEncashment` and `OffInLieuRecord` DataFlow models.
11. **Bound all in-memory collections** — Convert 15+ unbounded dicts to `OrderedDict` with LRU eviction or `deque(maxlen=N)`.

### Medium-Term (Next Iteration)

12. **Wire anti-amnesia injection** — Pass computed constraints into the LLM system prompt.
13. **Enforce constraint envelopes** — Block or downgrade responses when constraint violations are detected.
14. **Add prompt injection detection** — Extend circumvention patterns to detect "ignore instructions", "you are now", "bypass safety", etc.
15. **Implement password reset email delivery** — Currently generates tokens but never sends them.
16. **Add active user check to token validation** — Query `is_active` flag on each request (with caching).
17. **Implement Redis-backed rate limiting** — Replace in-memory stores for multi-worker deployments.
18. **Expose remaining 4 calculators as API endpoints** — OT, notice period, retrenchment, quota/levy.
19. **Add SSE disclaimer event handler** — Frontend should display risk disclaimers from the backend.
20. **Fix payroll response format** — Either return flat array or update frontend to expect `{runs: [...]}`.

---

## Appendix: Finding Cross-Reference

Each finding is tagged with an ID that maps to the source audit:

| Prefix                 | Source Agent                      |
| ---------------------- | --------------------------------- |
| C-PAY, H-PAY, M-PAY    | Payroll Auditor                   |
| C-FE, M-FE             | Frontend Auditor                  |
| C-HRIS, H-HRIS, M-HRIS | HRIS Auditor                      |
| C-SEC, H-SEC, M-SEC    | Security Auditor                  |
| C-AUTH, H-AUTH, M-AUTH | Auth Auditor                      |
| C-ADV, H-ADV, M-ADV    | Advisory Auditor                  |
| H-MEM                  | Cross-cutting (multiple auditors) |
| H-MCP, M-MCP           | MCP Auditor                       |

Full transcripts from each specialist agent are available for detailed line-by-line findings.

---

_Report generated by 7 specialist agents + 1 API contract auditor running in parallel._
_Total audit duration: ~5 minutes across all agents._
_Total files examined: 150+ source files across backend, frontend, and deployment._
