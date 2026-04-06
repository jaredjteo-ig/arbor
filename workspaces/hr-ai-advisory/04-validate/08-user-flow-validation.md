# Red Team Round 8: User Flow Validation

**Date**: 2026-04-06
**Scope**: Trace all documented user flows through actual backend + frontend code
**Documents validated**:

- `03-user-flows/01-core-user-flows.md`
- `03-user-flows/02-shadow-agent-flows.md`
- `03-user-flows/03-employee-onboarding-flow.md`
- `03-user-flows/04-byok-api-key-flows.md`
- `workspaces/ricoh-demo/03-user-flows/01-company-policy-user-flows.md`

---

## Executive Summary

Out of 7 critical user flows validated, 5 are largely functional with isolated gaps. Two areas have CRITICAL gaps: (1) public holidays are not seeded during company creation despite being documented, breaking leave day calculation accuracy, and (2) the advisory chat UI has no budget-exceeded handling, meaning users on the free tier hit a raw 429 error with no friendly message. A total of 21 gaps were identified: 2 CRITICAL, 6 HIGH, 8 MEDIUM, 5 LOW.

**Complexity Score**: 24 (Complex) -- Governance: 6, Legal/Compliance: 8, Strategic/UX: 10

---

## Flow 1: New User Onboarding

**Source**: `03-employee-onboarding-flow.md` Flow 1

### Trace

| Step                                    | Flow Document                                                   | Actual Code                                                                                          | Status                         |
| --------------------------------------- | --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------ |
| 1. Visitor lands on site                | Landing page                                                    | Landing page exists (ManagementShowcase)                                                             | PASS                           |
| 2. Clicks "Get Started Free" -> /signup | Standard registration form                                      | /signup now shows `InvitationOnlyNotice` (no self-service)                                           | CHANGED                        |
| 3. Signup -> POST /auth/register        | Creates user, auto-login                                        | `AuthContext.register()` -> POST /auth/register -> redirect to /onboarding                           | PASS (but unreachable from UI) |
| 4. Dashboard (no company)               | "Set Up Company" CTA                                            | /dashboard page imports `CompanySetupModal`                                                          | PASS                           |
| 5. Company Setup Modal (3 steps)        | Name, UEN, sector, headcount                                    | `CompanySetupModal` exists; calls `clientsApi.create()`                                              | PASS                           |
| 6. Auto-seeding after company creation  | 4 policies, 11 leave types, 4 claims, attendance, 2026 holidays | `seed_company_defaults()` seeds policies, leave types, claims, attendance -- but NOT public holidays | **FAIL**                       |

### Gaps

| #   | Step | Expected                                                        | Actual                                                                                                                                                                                                      | Severity     | Fix                                                                                                                                                                                                                                                                                                                               |
| --- | ---- | --------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 6    | 2026 public holidays seeded from data.gov.sg                    | `company_seeding.py` has no `_seed_public_holidays` function. The only holiday creation is via POST `/leave/public-holidays` (manual admin action) or the MCP regulatory server (tool_get_public_holidays). | **CRITICAL** | Add `_seed_public_holidays()` to `company_seeding.py` that fetches from data.gov.sg adapter (with hardcoded 2026 fallback). This directly affects leave day calculations since `_calculate_working_days()` queries `PublicHolidayListNode` and returns wrong totals when no holidays exist.                                       |
| 2   | 6    | 4 claim categories (Transport, Meals, Medical, Office Supplies) | `company_seeding.py` seeds 6 claim categories: Transport, Meals, Medical, Office Supplies, Entertainment, Training & Development                                                                            | LOW          | Documentation drift. The seeding is more generous than the flow spec. Not a bug -- update the flow document.                                                                                                                                                                                                                      |
| 3   | 2    | Self-service signup flow                                        | Signup page now shows "Registration by Invitation Only" when no token present. The `register` function still exists in AuthContext but has no UI path to it.                                                | MEDIUM       | The onboarding flow document (Flow 1) describes a self-service signup that no longer exists. The flow needs updating OR the onboarding must be made accessible post-login (for admins who were invited by a platform admin/seeded as first user). Currently the /onboarding page is reachable but not linked from the login flow. |
| 4   | 5    | Onboarding calls profile.create_company_profile                 | Onboarding page calls `clientsApi.create()` which hits `/clients` router, not `/profile` router. Both call `seed_company_defaults()`.                                                                       | LOW          | Two code paths for company creation (clients.py and profile.py). Both seed correctly, but the onboarding flow uses the clients path. Not a bug, but a maintenance risk.                                                                                                                                                           |

---

## Flow 2: Employee Invitation

**Source**: `03-employee-onboarding-flow.md` Flows 2 and 3

### Trace

| Step                                 | Flow Document                 | Actual Code                                                                | Status |
| ------------------------------------ | ----------------------------- | -------------------------------------------------------------------------- | ------ |
| 1. Admin navigates to /employees     | Employee roster shown         | `/employees/page.tsx` exists, "Invite Employee" button present             | PASS   |
| 2. Admin enters email, role          | POST /employees/invite        | Endpoint exists, creates invitation with 7-day expiry token                | PASS   |
| 3. Response returns invite_url       | Modal shows copyable link     | Response includes `invite_url` with token                                  | PASS   |
| 4. Employee clicks invite link       | /signup?token=abc123          | Signup page detects token, calls GET /employees/invite/{token}             | PASS   |
| 5. Token validation                  | Valid/expired/used states     | Full state machine: valid, expired, already_used, invalid, network_error   | PASS   |
| 6. Employee submits form             | POST /auth/register-employee  | Creates User + Employee + LeaveBalance records via `ensure_leave_balances` | PASS   |
| 7. Auto-login -> /my-dashboard       | JWT tokens returned, redirect | Tokens stored in localStorage, `router.push("/my-dashboard")`              | PASS   |
| 8. Employee sees employee navigation | Simplified navigation         | /my-dashboard page shows employment summary, leave balances                | PASS   |

### Gaps

| #   | Step       | Expected                                                                                           | Actual                                                                                                                                                                                             | Severity                       | Fix |
| --- | ---------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | --- |
| 5   | 3          | Flow says "Banner: You've been invited to join [Company Name]" with email pre-filled and read-only | `InviteBanner` component shows company name and role. Email field is pre-filled and read-only.                                                                                                     | PASS                           |
| 6   | 6          | "Backend creates: User + Employee + LeaveBalance (7 annual, 14 sick)"                              | `ensure_leave_balances()` creates balances for ALL configured leave types (not just annual/sick). Initial entitlement is from `LeaveTypeConfig.default_days`, which includes 7 annual and 14 sick. | PASS (more thorough than spec) |
| 7   | Error Flow | "Already Used" shows "Log in to access your account" link                                          | `InviteError` shows login link when `showLoginLink=true` for `already_used` state                                                                                                                  | PASS                           |

**Verdict**: This flow is fully functional. No gaps found.

---

## Flow 3: First Payroll Run

**Source**: `03-employee-onboarding-flow.md` Flow 4

### Trace

| Step                                     | Flow Document                             | Actual Code                                                                                                                                   | Status |
| ---------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1. Admin navigates to /payroll           | Sees employee roster                      | `/payroll/page.tsx` exists                                                                                                                    | PASS   |
| 2. Creates payroll run (month selection) | POST /payroll/calculate with period       | Endpoint exists, accepts period_start, period_end, pay_date                                                                                   | PASS   |
| 3. System calculates CPF, SDL, SHG, FWL  | Deterministic payroll calculator          | `payroll_calculator.py` implements all four: CPF (age-band), SDL (min $2 / max $11.25), SHG (race-based CDAC/MBMF/SINDA/ECF), FWL (pass_type) | PASS   |
| 4. Admin reviews payslips                | Run in 'draft' status                     | Run created with status="draft", payslips generated per employee                                                                              | PASS   |
| 5. Approve payroll run                   | POST /payroll/runs/{id}/approve           | Endpoint exists, moves status to "approved"                                                                                                   | PASS   |
| 6. Mark paid                             | POST /payroll/runs/{id}/mark-paid         | Endpoint exists, moves status to "paid"                                                                                                       | PASS   |
| 7. Payslip PDF generation                | POST /payroll/runs/{id}/payslips/{id}/pdf | Endpoint exists, generates HTML payslip (client renders to PDF)                                                                               | PASS   |
| 8. Employee views /my-payslips           | GET /payroll/my-payslips                  | Endpoint exists, returns payslips for the authenticated employee                                                                              | PASS   |

### Gaps

| #   | Step         | Expected                                                                     | Actual                                                                                                                                                                                  | Severity | Fix                                                                                                                                                                                                                                                                                  |
| --- | ------------ | ---------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 8   | 3            | FWL rates should vary by sector and tier (WP $300, S Pass $450 per flow doc) | `_get_fwl_rate()` uses flat estimates -- comment says "Production: look up from rate tables based on sector"                                                                            | HIGH     | The FWL rate lookup is not sector-aware. The function returns flat rates without considering the company's sector. This means FWL calculations for manufacturing, construction, etc. will use incorrect rates. The rate table needs to be expanded to include sector-specific tiers. |
| 9   | 7            | PDF export                                                                   | The endpoint returns HTML, not PDF. Comment says "can be rendered to PDF by client or weasyprint" but there is no evidence of client-side PDF rendering in the frontend.                | MEDIUM   | The `/payroll/page.tsx` frontend would need to use a library like `html2pdf.js` or `react-to-print` to render the HTML response as a downloadable PDF. Currently unclear if this is handled.                                                                                         |
| 10  | Cross-module | Payroll should pull leave deductions, overtime, claims                       | Code pulls unpaid leave, approved timesheets OT hours, and approved claims. However, `leave_type_code: "unpaid"` filter may miss other unpaid leave types (e.g., `unpaid_infant_care`). | MEDIUM   | The unpaid leave filter should match all leave types where `is_paid=False`, not just `leave_type_code="unpaid"`. This could miss `unpaid_infant_care` leave applications.                                                                                                            |

---

## Flow 4: Advisory Chat

**Source**: `01-core-user-flows.md` Flow 2

### Trace

| Step                              | Flow Document                           | Actual Code                                                                                                                                                                                                           | Status |
| --------------------------------- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1. User types question            | Natural language input                  | `/advisory/page.tsx` with `ChatContainer` + `ConversationSidebar`                                                                                                                                                     | PASS   |
| 2. Streaming response             | SSE word-by-word                        | POST /advisory/stream returns StreamingResponse with SSE events                                                                                                                                                       | PASS   |
| 3. Safety chain                   | 13-step pipeline                        | Input sanitisation, rate limiting, scope check, injection detection, query screening, EATP genesis, anti-amnesia, KB retrieval, citation validation, disclaimer generation, response screening, trust chain recording | PASS   |
| 4. Risk tier coloring             | Green/Amber/Red based on risk level     | Response includes `risk_tier` field; frontend `RiskTierBadge` renders color-coded                                                                                                                                     | PASS   |
| 5. Citation links                 | Source citation pills                   | `CitationValidationResult` produces validated citations; frontend renders as pills                                                                                                                                    | PASS   |
| 6. Conversation persistence       | History sidebar with past conversations | GET /advisory/conversations + GET /advisory/history/{id}                                                                                                                                                              | PASS   |
| 7. Follow-up in same conversation | Conversation memory                     | `ShortTermMemory` per conversation_id, bounded OrderedDict (10k max)                                                                                                                                                  | PASS   |

### Gaps

| #   | Step           | Expected                                                          | Actual                                                                                                                                                                                                                                                     | Severity     | Fix                                                                                                                                                                                                                                                                  |
| --- | -------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 11  | Budget check   | "Budget exceeded" -> friendly message in chat (per BYOK flow doc) | Backend returns 429 JSON with `"error": "budget_exceeded"` message. Frontend advisory components (`ChatContainer.tsx`, `sse.ts`, `advisory.ts`) have **no handling for 429/budget_exceeded responses**. The SSE stream would fail with an unhandled error. | **CRITICAL** | Add budget-exceeded detection in the SSE streaming client. When the stream endpoint returns 429, display the friendly message from the BYOK flow document: "Your company's free AI allowance has been used this month..." with a "Go to Settings" button for admins. |
| 12  | Budget warning | "3 of ~500 free queries this month" indicator                     | No query count or budget indicator is shown in the advisory chat interface. The budget bar only exists on `/settings/ai`.                                                                                                                                  | HIGH         | Add a subtle budget usage indicator to the advisory chat footer, as specified in BYOK Flow 1.                                                                                                                                                                        |
| 13  | Flow doc       | "Download related template" follow-up option                      | Advisory responses do not include template download links. Document generation is a separate flow.                                                                                                                                                         | LOW          | This is a documented future feature, not a current gap.                                                                                                                                                                                                              |

---

## Flow 5: Leave Application

**Source**: `03-employee-onboarding-flow.md` Flow 5 and `02-shadow-agent-flows.md` Flow 3

### Trace

| Step                               | Flow Document                            | Actual Code                                                                   | Status                                |
| ---------------------------------- | ---------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------- |
| 1. Employee navigates to /my-leave | Balance overview, apply button           | `/my-leave/page.tsx` shows leave balance cards with statutory defaults        | PASS                                  |
| 2. Apply leave                     | POST /leave/apply                        | Endpoint validates dates, calculates working days, checks balance and overlap | PASS                                  |
| 3. Balance checking                | Available = entitlement - used - pending | Exact formula implemented in apply_leave                                      | PASS                                  |
| 4. Overlap detection               | Reject if overlapping                    | `_check_overlapping_applications()` called before creation                    | PASS                                  |
| 5. Working day calculation         | Excludes weekends and public holidays    | `_calculate_working_days()` queries `PublicHolidayListNode`                   | PASS (dependent on holidays existing) |
| 6. Manager approval                | PATCH /leave/applications/{id}/approve   | Endpoint exists, moves pending_days to used_days                              | PASS                                  |
| 7. Rejection                       | PATCH /leave/applications/{id}/reject    | Endpoint exists, releases pending_days                                        | PASS                                  |
| 8. Withdrawal                      | PATCH /leave/applications/{id}/withdraw  | Endpoint exists                                                               | PASS                                  |

### Gaps

| #   | Step | Expected                                         | Actual                                                                                                                                                                                                                     | Severity                          | Fix                                                                                                                                                                                          |
| --- | ---- | ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 14  | 5    | Working day calculation excludes public holidays | Correct code exists, but if public holidays are not seeded (Gap #1), ALL public holidays are treated as working days. For a 5-day leave spanning Chinese New Year, the system would calculate 5 working days instead of 3. | HIGH (cascading from CRITICAL #1) | This is a cascading effect of Gap #1. Once public holidays are seeded during company creation, this calculation becomes correct.                                                             |
| 15  | 2    | Half-day leave support                           | `start_half` and `end_half` parameters accepted (first_half, second_half, full_day). Calculation reduces day count by 0.5 for half-day flags.                                                                              | PASS                              |
| 16  | 6    | Approval should notify the employee              | No notification mechanism (email/push/in-app) on approval or rejection. Only the leave balance is updated.                                                                                                                 | HIGH                              | The leave approval and rejection endpoints update the database status and balance, but do not trigger any notification to the employee. The employee must manually check their leave status. |

---

## Flow 6: BYOK API Key Flow

**Source**: `04-byok-api-key-flows.md`

### Trace

| Step                                 | Flow Document                                | Actual Code                                                                                              | Status      |
| ------------------------------------ | -------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------- |
| 1. AI works immediately (server key) | No setup needed                              | `build_llm_context()` falls back to server `.env` key                                                    | PASS        |
| 2. Settings > AI Configuration page  | Budget bar, provider options                 | `/settings/ai/page.tsx` with BudgetBar, PROVIDERS list (6 providers)                                     | PASS        |
| 3. Admin enters API key              | Form with validate & save                    | POST /{company_id}/llm-config with encrypted key                                                         | PASS        |
| 4. Key validation                    | Minimal API call to verify                   | POST /{company_id}/llm-config/validate -- Ollama hits /api/tags, cloud providers make minimal completion | PASS        |
| 5. Key encryption at rest            | Encrypted before storage                     | `encrypt_api_key()` called before DB write                                                               | PASS        |
| 6. Ollama configuration              | Endpoint + model fields                      | Form for base_url and model, validation tests reachability                                               | PASS        |
| 7. Provider resolution priority      | BYOK > Server key > Ollama localhost         | `build_llm_context()`: user config > company config > server env                                         | PASS        |
| 8. Key becomes invalid               | Fall back to server key, mark status=invalid | Advisory detects 401, marks config invalid -- **but need to verify**                                     | PARTIAL     |
| 9. Budget warning at 80%             | Warning banner in chat                       | Budget bar on settings page shows warning. **Not shown in chat.**                                        | See Gap #12 |
| 10. Budget exceeded at 100%          | Friendly message, no LLM call                | Backend returns 429 with message. Frontend does not handle.                                              | See Gap #11 |

### Gaps

| #   | Step | Expected                                                           | Actual                                                                                                                                                                                                                                                                                                                                                  | Severity | Fix                                                                                                                                                                                                              |
| --- | ---- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 17  | 8    | "Key Invalid" -> fall back to server key, show warning in response | The advisory engine `advisory.py` resolves LLM context before the query. If the BYOK key returns a 401, the error is caught in the Kaizen provider, but the fallback to server key is not automated in the advisory flow itself. The config is not automatically marked as "invalid" on failed API calls -- only the validate endpoint checks validity. | HIGH     | Add error handling in `AdvisoryEngine` or the Kaizen provider patch: when the LLM call fails with 401/403, mark the config status as "invalid" and retry with server defaults. Return a warning in the response. |
| 18  | 10   | Employee sees "Ask your admin" when budget exceeded                | Backend returns a generic budget-exceeded message. There is no role-based messaging (admin gets "Go to Settings" vs employee gets "Ask your admin").                                                                                                                                                                                                    | MEDIUM   | The 429 response body message is the same for all users. Add `role` to the response or let the frontend differentiate based on the user's role from AuthContext.                                                 |
| 19  | Edge | "Remove Key" -> hard-delete encrypted key                          | `delete_llm_config()` soft-deletes (is_active=False) but also clears encrypted_key field. Audit trail preserved.                                                                                                                                                                                                                                        | PASS     |

---

## Flow 7: Policy Upload

**Source**: `workspaces/ricoh-demo/03-user-flows/01-company-policy-user-flows.md`

### Trace

| Step                                 | Flow Document                         | Actual Code                                                                            | Status |
| ------------------------------------ | ------------------------------------- | -------------------------------------------------------------------------------------- | ------ |
| 1. HR manager clicks "Add Policy"    | Drawer opens on /policies             | `/policies/page.tsx` has `PolicyCreateModal`                                           | PASS   |
| 2. Category selection (9 predefined) | 9 categories shown                    | `CATEGORY_LABELS` in policies page: 9 categories matching flow                         | PASS   |
| 3. Manual text entry                 | POST /policies                        | Endpoint accepts title, category, content, status                                      | PASS   |
| 4. File upload (PDF/DOCX)            | POST /policies/upload                 | Multipart upload, max 10MB, text extraction via `policy_parser.extract_text()`         | PASS   |
| 5. Statutory floor check             | Warning if below minimums             | `check_policy_against_statutory_floor()` called on create and upload; returns warnings | PASS   |
| 6. Draft vs Publish                  | status="draft" or "active"            | Both statuses supported in create endpoint                                             | PASS   |
| 7. Employee acknowledgment           | POST /policies/{id}/acknowledge       | Endpoint exists, tracks per-employee per-version acknowledgment                        | PASS   |
| 8. Pending acknowledgments           | GET /policies/pending-acknowledgments | Endpoint exists, returns policies needing ack that employee hasn't acknowledged        | PASS   |
| 9. Version history                   | GET /policies/{id}/versions           | Endpoint exists                                                                        | PASS   |

### Gaps

| #   | Step         | Expected                                                  | Actual                                                                                                                                                                                                                                        | Severity | Fix                                                                                                                                                                                                                   |
| --- | ------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 20  | Flow doc API | `PATCH /api/policies/:id/status` to publish               | No dedicated status-change endpoint. Status is updated via `PUT /policies/{id}` (full update). The flow document specifies a separate `PATCH` status endpoint and a separate `POST /distribute` endpoint, neither of which exist.             | MEDIUM   | The actual implementation uses `PUT /policies/{id}` for all updates including status changes. This works but diverges from the flow spec. Either update the flow document or add the specific endpoints.              |
| 21  | Flow doc API | `POST /api/policies/:id/distribute` to send notifications | No notification distribution endpoint exists. When a policy is published with `requires_acknowledgment=true`, no notifications are sent to employees. They must discover pending acknowledgments via the `/pending-acknowledgments` endpoint. | HIGH     | Implement a notification mechanism for policy distribution. At minimum, create pending notification records that the employee dashboard polls. Ideally, integrate with email (SendGrid) or in-app push notifications. |

---

## Summary: Risk Register

| #   | Risk                                                  | Likelihood                                 | Impact                                                 | Severity     | Mitigation                                                                                             |
| --- | ----------------------------------------------------- | ------------------------------------------ | ------------------------------------------------------ | ------------ | ------------------------------------------------------------------------------------------------------ |
| 1   | Public holidays not seeded on company creation        | Certain (every new company)                | Leave calculations wrong for all employees             | **CRITICAL** | Add `_seed_public_holidays()` to `company_seeding.py` with data.gov.sg fetch + hardcoded 2026 fallback |
| 11  | Budget exceeded not handled in advisory chat UI       | Certain (hits every free-tier user at cap) | Raw 429 error in chat, no recovery path                | **CRITICAL** | Add budget-exceeded detection in SSE client with friendly inline message                               |
| 8   | FWL rates not sector-specific                         | Likely (any company with foreign workers)  | Incorrect payroll calculations for WP/SP holders       | **HIGH**     | Expand `_get_fwl_rate()` with sector-specific tier tables                                              |
| 12  | No budget usage indicator in advisory chat            | Certain                                    | Users unaware of approaching limit                     | **HIGH**     | Add query count/budget indicator to chat footer                                                        |
| 14  | Leave day calculation wrong without holidays          | Certain (cascading from #1)                | Employees overcharged leave days                       | **HIGH**     | Resolved by fixing #1                                                                                  |
| 16  | No notification on leave approval/rejection           | Certain                                    | Employees unaware of status changes                    | **HIGH**     | Add notification triggers on leave status transitions                                                  |
| 17  | BYOK key invalidity not auto-detected                 | Moderate                                   | User's query fails, no automatic fallback              | **HIGH**     | Add 401 handling in LLM call path with auto-fallback                                                   |
| 21  | No policy distribution notifications                  | Certain                                    | Employees unaware of new policies requiring ack        | **HIGH**     | Implement notification system for policy distribution                                                  |
| 3   | Onboarding flow doc outdated (no self-service signup) | N/A (documentation)                        | Confusion during development                           | **MEDIUM**   | Update flow documents to reflect invitation-only model                                                 |
| 9   | Payslip PDF not rendered on frontend                  | Likely                                     | Admin cannot download PDF payslips                     | **MEDIUM**   | Implement client-side PDF rendering from HTML response                                                 |
| 10  | Unpaid leave filter misses unpaid_infant_care         | Moderate                                   | Payroll deduction missed for some leave types          | **MEDIUM**   | Filter on `is_paid=False` from LeaveTypeConfig instead of `leave_type_code="unpaid"`                   |
| 18  | Budget exceeded message not role-aware                | Certain                                    | Employee sees generic message without "Ask your admin" | **MEDIUM**   | Differentiate message by user role                                                                     |
| 20  | Policy API diverges from flow spec                    | N/A (documentation)                        | Developer confusion                                    | **MEDIUM**   | Reconcile flow document with actual API design                                                         |
| 2   | Seeding creates 6 claim categories (flow says 4)      | N/A                                        | No user impact                                         | **LOW**      | Update flow document                                                                                   |
| 4   | Two company creation paths (clients + profile)        | N/A                                        | Maintenance risk                                       | **LOW**      | Consolidate into one path                                                                              |
| 13  | "Download template" follow-up not in advisory         | N/A                                        | Future feature                                         | **LOW**      | Track as enhancement                                                                                   |

---

## Cross-Reference Audit

- **`company_seeding.py`** -- Missing public holidays seeding. Seeds 11 items (policies, leave types, claim categories, attendance, cost centres, pay items, projects, project roles, inventory, appraisals, job listings) but not public holidays.
- **`leave.py` -> `_calculate_working_days()`** -- Depends on `PublicHolidayListNode` which returns empty results for new companies.
- **`advisory.py` stream endpoint** -- Returns 429 JSON for budget exceeded, but the frontend SSE client does not parse non-SSE responses.
- **`payroll_calculator.py` -> `_get_fwl_rate()`** -- Comment explicitly says "Production: look up from rate tables based on sector" but this was never implemented.
- **Flow documents** -- `01-core-user-flows.md` and `03-employee-onboarding-flow.md` describe self-service signup which was disabled in commit `73fefac`.
- **Policy flow document** -- Specifies 5 API endpoints but only 3 exist in the actual API (create, upload, acknowledge). The PATCH status and POST distribute endpoints are missing.

---

## Decision Points

- Should public holidays be fetched live from data.gov.sg at company creation time, or should a hardcoded 2026 calendar be used with annual refresh?
- Should the budget-exceeded state in advisory be handled as an SSE event (allowing the stream endpoint to return a proper SSE "error" event) or as a pre-check before the stream?
- Should the policy distribution notification system use email (SendGrid), in-app notifications, or both?
- Should the self-service onboarding flow be removed from documentation entirely, or retained as a future feature?
- For FWL rates, should the sector be pulled from the company profile, or should the admin select the correct MOM sector classification separately?

---

## Priority Fix Order

1. **Gap #1 (CRITICAL)**: Seed public holidays during company creation -- directly breaks leave calculations for every company
2. **Gap #11 (CRITICAL)**: Handle budget-exceeded in advisory chat UI -- breaks free-tier user experience
3. **Gap #8 (HIGH)**: FWL sector-specific rates -- financial accuracy
4. **Gap #16 (HIGH)**: Leave approval notifications -- core workflow gap
5. **Gap #21 (HIGH)**: Policy distribution notifications -- compliance workflow gap
6. **Gap #17 (HIGH)**: BYOK auto-fallback on invalid key -- reliability
7. **Gap #12 (HIGH)**: Budget indicator in advisory chat -- user awareness
8. Remaining MEDIUM and LOW gaps
