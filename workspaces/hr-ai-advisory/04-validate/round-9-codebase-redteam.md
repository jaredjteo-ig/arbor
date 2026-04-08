# Red Team Report: Round 9 — Full Web Codebase Audit

**Date**: 2026-04-08
**Agents**: UI/UX Designer, Security Reviewer, Value Auditor, Deep Analyst, RBAC Auditor
**Scope**: All frontend pages (apps/web/src/) + backend API (src/hr_advisory/)

---

## Executive Summary

The Arbor/Central platform is remarkably complete — 50+ pages, 8 HRIS modules, 7 calculators, AI advisory with 13-step safety chain, and proper Singapore regulatory specificity. The substance is all there.

However, 5 red team agents found **2 blockers, 5 critical, and 12 high-severity issues** that must be fixed before production use. The top 3 problems:

1. **The front door is locked** — Landing page only has "Login" buttons, no signup path for new company owners
2. **PII stored in plaintext** — Employee self-service profile saves don't encrypt NRIC/bank numbers
3. **Employees can see admin pages** — No frontend route guards; typing `/payroll` or `/reports` in the URL works

---

## BLOCKERS (Fix before any demo)

### B-1: No self-service signup path for company owners

- **Source**: Value Auditor, Deep Analyst
- **Issue**: Landing page CTAs all say "Login" → /login. The /signup page says "Registration by Invitation Only." A new SME owner discovering the product has no way to create an account.
- **Files**: `apps/web/src/app/page.tsx`, `apps/web/src/components/management/ManagementShowcase.tsx` (line 279)
- **Impact**: Zero new user acquisition. The onboarding wizard (/onboarding) exists and is excellent but is unreachable.
- **Fix**: Add "Get Started Free" CTA linking to owner registration → onboarding flow

### B-2: Landing page CTA text says "Login" instead of "Get Started Free"

- **Source**: Value Auditor
- **Issue**: Every button on the landing page says "Login" — hero, features CTA, bottom CTA, compliance link. This signals "existing users only."
- **Files**: `apps/web/src/app/page.tsx` (multiple locations), ManagementShowcase `isPublic` mode
- **Fix**: Change CTA text and routing for unauthenticated visitors

---

## CRITICAL (Fix before deploy)

### C-1: Self-service profile update stores NRIC/bank in PLAINTEXT

- **Source**: Security Reviewer
- **Issue**: `PUT /employees/me` does NOT call `encrypt_field()` on nric_fin or bank_account_number. Compare with `PATCH /employees/{id}` (admin update) which correctly encrypts. Mixed encrypted/plaintext state in the database.
- **File**: `src/hr_advisory/api/routers/employees.py`, lines 1930-1951
- **Impact**: PDPA violation — Singapore NRIC and bank account numbers stored unencrypted at rest.

### C-2: Masked PII data corruption on save-without-change

- **Source**: Security Reviewer
- **Issue**: GET /employees/me returns masked values ("S\*\*\*\*567D"). Profile page loads these into form fields. Clicking Save without editing sends the mask string back, permanently overwriting the encrypted original.
- **Files**: `apps/web/src/app/(dashboard)/my-profile/page.tsx`, backend `PUT /employees/me`
- **Impact**: Permanent data loss of encrypted NRIC/bank numbers. Payroll/CPF/tax filing will operate on corrupted data.

### C-3: Auth rate limiting allows 120 login attempts per minute

- **Source**: Security Reviewer
- **Issue**: `_check_auth_rate_limit` uses defaults of 120 requests/60 seconds. A stricter config (5/minute) exists in validation.py but is never wired up.
- **File**: `src/hr_advisory/api/routers/auth.py`, lines 26-34
- **Impact**: No brute force protection. Weak passwords compromised in minutes.

### C-4: Employee "My Leave" nav links to /leave (admin page)

- **Source**: UI/UX Designer
- **Issue**: Employee sidebar "My Leave" href is `/leave` which is the admin leave management page. Should be `/my-leave`.
- **File**: `apps/web/src/components/shell/NavigationSidebar.tsx`, line 263
- **Impact**: Employees routed to admin leave view instead of their personal leave page.

### C-5: /my-leave has no "Apply Leave" button

- **Source**: Deep Analyst, UI/UX Designer
- **Issue**: The employee /my-leave page shows balances but has zero leave application functionality. The ApplyLeaveModal exists only on the admin /leave page. Backend POST /leave/apply is implemented but unreachable from employee self-service.
- **File**: `apps/web/src/app/(dashboard)/my-leave/page.tsx`
- **Impact**: Employees cannot apply for leave — the core self-service flow is broken.

---

## HIGH (Fix before production)

### H-1: No frontend route-level RBAC — employees can access admin pages by URL

- **Source**: RBAC Auditor, UI/UX Designer, Security Reviewer
- **Issue**: ProtectedRoute supports `requiredRoles` prop but it is never used. Sidebar hides admin links for employees, but typing `/payroll`, `/employees`, `/reports`, `/analytics` in the URL loads those pages.
- **Files**: `apps/web/src/app/(dashboard)/layout.tsx`, `apps/web/src/components/auth/ProtectedRoute.tsx`
- **Backend mitigation**: API endpoints use `require_role()` so data is protected, but page shells render.

### H-2: /compliance API open to all authenticated users (no role check)

- **Source**: RBAC Auditor
- **Issue**: `GET /compliance/status/{company_id}` uses `get_current_user` not `require_role`. Employees can access company compliance data.
- **File**: `src/hr_advisory/api/routers/compliance.py`

### H-3: /reports and /analytics pages unguarded (frontend + partial backend)

- **Source**: RBAC Auditor
- **Files**: `apps/web/src/app/(dashboard)/reports/page.tsx`, `apps/web/src/app/(dashboard)/analytics/page.tsx`

### H-4: NRIC/bank displayed unmasked in profile form

- **Source**: UI/UX Designer
- **Issue**: Full NRIC and bank account numbers rendered in plain text inputs. `nric_fin_last4` and `bank_account_last4` fields exist but are never used for display.
- **File**: `apps/web/src/app/(dashboard)/my-profile/page.tsx`, lines 447-452, 534
- **Impact**: PDPA risk — screen sharing, shoulder surfing exposure.

### H-5: JWT tokens stored in localStorage (XSS-vulnerable)

- **Source**: Security Reviewer
- **Issue**: Both access and refresh tokens in localStorage. Any XSS vulnerability allows token exfiltration. Refresh tokens valid for 7 days.
- **Files**: `apps/web/src/contexts/AuthContext.tsx`, `apps/web/src/services/api/client.ts`

### H-6: Google OAuth auto-creates accounts for anyone

- **Source**: Security Reviewer
- **Issue**: Any Google account can create a user account in the system. No invitation or domain restriction.
- **File**: `src/hr_advisory/api/routers/auth.py`, lines 712-723

### H-7: Encryption fallback silently stores plaintext

- **Source**: Security Reviewer
- **Issue**: When `SALARY_ENCRYPTION_KEY` is unset, `encrypt_field()` returns plaintext with only a log warning. No alarm.
- **File**: `src/hr_advisory/security/encryption.py`, lines 30-37

### H-8: Password reset endpoint lacks rate limiting

- **Source**: Security Reviewer
- **File**: `src/hr_advisory/api/routers/auth.py`, lines 345-382

### H-9: No rate limiting on leave/claims endpoints

- **Source**: Deep Analyst
- **Issue**: Leave router has zero `check_rate_limit` calls. POST /leave/apply unprotected against abuse.
- **File**: `src/hr_advisory/api/routers/leave.py`

### H-10: Emergency Contact section has non-functional Save button

- **Source**: UI/UX Designer
- **Issue**: Save button exists but handler is empty. Shows "coming soon" text. Button triggers save animation but saves nothing.
- **File**: `apps/web/src/app/(dashboard)/my-profile/page.tsx`, lines 564-566

### H-11: No client-side form validation on profile page

- **Source**: UI/UX Designer
- **Issue**: No NRIC format validation, no postal code check, no phone format check. Required fields can be submitted empty.
- **File**: `apps/web/src/app/(dashboard)/my-profile/page.tsx`

### H-12: No "why it's free" trust signals on landing page

- **Source**: Value Auditor
- **Issue**: "100% Free" stated but no supporting evidence — no open source mention, no "no credit card," no trust-building.
- **File**: `apps/web/src/app/page.tsx`

---

## MEDIUM (Fix in next sprint)

| #    | Issue                                                                          | Source        | File                       |
| ---- | ------------------------------------------------------------------------------ | ------------- | -------------------------- |
| M-1  | "My Claims" nav links to shared /claims (not /my-claims)                       | UI/UX         | NavigationSidebar.tsx:269  |
| M-2  | "My Attendance" nav links to shared /attendance                                | UI/UX         | NavigationSidebar.tsx:281  |
| M-3  | In-memory token blocklist lost on server restart                               | Security      | token_blocklist.py         |
| M-4  | TOCTOU race in invitation acceptance                                           | Security      | auth.py:440-484            |
| M-5  | Compliance snapshot in onboarding is client-side only (not real backend check) | Deep Analyst  | ComplianceSnapshotStep.tsx |
| M-6  | Password reset email not actually sent (no SendGrid)                           | Deep Analyst  | auth.py:318-330            |
| M-7  | Shadow agent pattern learning not persisted                                    | Deep Analyst  | ShadowAgentContext         |
| M-8  | Budget-exceeded state in advisory contradicts "100% Free" claim                | Value Auditor | ChatContainer.tsx:38-39    |
| M-9  | Brand inconsistency (Arbor in code, Central in UI)                             | Value Auditor | Multiple files             |
| M-10 | Invite token validation endpoint public and un-rate-limited                    | Security      | employees.py:1417-1486     |
| M-11 | str(exc) leaked in some API error responses                                    | Security      | auth.py:74,78,84,140       |

---

## LOW (Backlog)

| #   | Issue                                                     | Source        |
| --- | --------------------------------------------------------- | ------------- |
| L-1 | User dropdown shows no name/email/role                    | UI/UX         |
| L-2 | Heading hierarchy skips h2 on dashboards                  | UI/UX         |
| L-3 | Keyboard focus style missing hover background on dropdown | UI/UX         |
| L-4 | Default JWT secret predictable in dev                     | Security      |
| L-5 | NRIC format not validated on backend                      | Security      |
| L-6 | CSP header may not apply to Next.js frontend              | Security      |
| L-7 | Two different rate limiter implementations                | Security      |
| L-8 | Reports page has "Coming Soon" items visible              | Value Auditor |

---

## What Passed

- All 50+ pages load with HTTP 200
- Employee invite → signup → auto-login flow is complete
- Payroll engine is comprehensive (CPF, SDL, FWL, SHG, IR8A, bank files)
- Advisory 13-step safety chain is the strongest component
- Calculators are deterministic with correct 2026 rates
- Error flows (expired/invalid/used tokens) properly handled
- Session management (proactive token refresh, auto-logout) is solid
- SQL injection prevention via DataFlow parameterized queries
- XSS prevention (no dangerouslySetInnerHTML)
- Password hashing (bcrypt, 72-byte limit)
- Tenant isolation (company-scoped access)
- Employee self-access protection (validate_employee_self_access)
- Prompt injection protection in advisory

---

## Recommended Fix Order

1. **C-1 + C-2**: Fix PII encryption on self-service + mask corruption (security emergency)
2. **C-3**: Tighten auth rate limiting to 5/minute
3. **C-4 + C-5**: Fix My Leave nav + add Apply Leave button
4. **H-1 + H-2 + H-3**: Add frontend route guards + compliance API role checks
5. **H-4**: Mask NRIC/bank in profile display
6. **B-1 + B-2**: Add self-service signup for company owners (requires product decision)
7. **H-6**: Restrict Google OAuth to invited users only
8. **H-7**: Make encryption key mandatory in production
9. **H-5**: Move tokens to httpOnly cookies (larger effort)
10. Everything else
