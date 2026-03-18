# Plan: Employee Onboarding Completion (v2 — post red-team)

## Objective

Complete the employee lifecycle from admin invite → employee registration → first payroll run. Close all critical gaps identified in the onboarding audit and red team reviews.

## Workstreams

### WS0: Backend Hardening (Prerequisites)

**Goal**: Fix data integrity and security issues before building new features.

| Task  | Description                                                                                          | Effort | Red Team Ref |
| ----- | ---------------------------------------------------------------------------------------------------- | ------ | ------------ |
| WS0.1 | Fix paternity leave seed: 14 → 28 days (CDCSA 2025 amendment)                                        | Tiny   | RT-1         |
| WS0.2 | Add invitation rollback on user creation failure (try/except in register-employee)                   | Small  | RT-3         |
| WS0.3 | Add duplicate invitation guard (check existing active invite + existing user for same email+company) | Small  | RT-8         |
| WS0.4 | Add company_name to validate_invitation response (lookup company record)                             | Small  | RT-5         |
| WS0.5 | Unify company creation seeding: create `seed_company_defaults(company_id)` shared function           | Medium | RT-2         |
| WS0.6 | Add invitation revocation endpoint (DELETE /employees/invite/{id})                                   | Small  | RT-13        |

**Dependencies**: None — do first

### WS1: Default Data Seeding (Backend)

**Goal**: When a company is created, all HRIS modules are immediately usable.

| Task  | Description                                                                                      | Effort |
| ----- | ------------------------------------------------------------------------------------------------ | ------ |
| WS1.1 | Call `_seed_statutory_leave_types(company_id)` inside `seed_company_defaults()`                  | Small  |
| WS1.2 | Create `_seed_default_claim_categories(company_id)` — Transport, Meals, Medical, Office Supplies | Small  |
| WS1.3 | Create `_seed_attendance_settings(company_id)` — persist existing defaults to DB                 | Small  |
| WS1.4 | Create `_seed_public_holidays(company_id)` — fetch from data.gov.sg with hardcoded 2026 fallback | Medium |
| WS1.5 | Wire `seed_company_defaults()` into BOTH POST /clients/ AND POST /profile/ handlers              | Small  |

**Dependencies**: WS0.5 (unified seed function)

### WS2: Invite Token & Leave Entitlement Fixes (Backend)

**Goal**: Admin can get invite links. Leave balances are correct.

| Task  | Description                                                                                                  | Effort | Red Team Ref |
| ----- | ------------------------------------------------------------------------------------------------------------ | ------ | ------------ |
| WS2.1 | Modify POST /employees/invite to return `invite_url` containing token                                        | Small  | ADR-1        |
| WS2.2 | Return tokens in CSV import response                                                                         | Small  | RT-12        |
| WS2.3 | Implement lazy LeaveBalance creation: when employee views leave or applies, auto-create from LeaveTypeConfig | Medium | RT-6         |
| WS2.4 | Respect `applicable_gender` and `min_service_months` in balance creation                                     | Medium | RT-9         |
| WS2.5 | Fix register-employee: use LeaveTypeConfig for initial balances instead of hardcoded 7/14                    | Small  | RT-6         |

**Dependencies**: WS1 (leave types must be seeded first)

### WS3: Employee Invite Acceptance Page (Frontend)

**Goal**: Employees can register via invite link.

| Task  | Description                                                                             | Effort | Red Team Ref |
| ----- | --------------------------------------------------------------------------------------- | ------ | ------------ |
| WS3.1 | Detect `token` query param on /signup page                                              | Small  | ADR-3        |
| WS3.2 | Validate token: call GET /employees/invite/{token}, show company name + role            | Medium | RT-5         |
| WS3.3 | Switch form: pre-fill email (read-only from invite), name + password fields only        | Medium |              |
| WS3.4 | Hide Google SSO when in invite mode (prevents token bypass)                             | Small  | RT-14        |
| WS3.5 | On submit: call POST /auth/register-employee                                            | Small  |              |
| WS3.6 | On success: auto-login with returned tokens, redirect to /my-dashboard                  | Small  |              |
| WS3.7 | Error states: invalid/expired/used token with clear messaging                           | Small  |              |
| WS3.8 | Admin employees page: show copyable invite link after invite, pending invitations table | Medium | RT-13        |

**Dependencies**: WS0 (company_name in validate response), WS2 (token returned)

### WS4: Public Landing Page (Frontend)

**Goal**: Visitors see a compelling product page before login.

| Task  | Description                                                                   | Effort | Red Team Ref |
| ----- | ----------------------------------------------------------------------------- | ------ | ------------ |
| WS4.1 | Create `app/page.tsx` (public route, no auth) using ManagementShowcase        | Medium | ADR-4        |
| WS4.2 | Fix CTA: link to /signup (not CompanySetupModal) for unauthenticated visitors | Small  | RT-10        |
| WS4.3 | Add navigation header with Login/Sign Up buttons                              | Small  |              |
| WS4.4 | Update ValuePropositionPanel to match HRIS positioning (not advisory-only)    | Small  | RT-11        |
| WS4.5 | Ensure root layout doesn't wrap public page in ProtectedRoute                 | Small  |              |

**Dependencies**: None — can run in parallel with WS0-WS2

### WS5: End-to-End Verification

**Goal**: Verify complete flow works admin invite → employee payslip.

| Task  | Description                                                                                                | Effort |
| ----- | ---------------------------------------------------------------------------------------------------------- | ------ |
| WS5.1 | E2E: admin creates company → verify seeded data (11 leave types, 4 claim categories, holidays, attendance) | Medium |
| WS5.2 | E2E: admin invites employee → gets link → employee registers → appears in roster                           | Medium |
| WS5.3 | E2E: verify employee leave balances respect applicable_gender and min_service_months                       | Medium |
| WS5.4 | E2E: employee self-service pages load (my-dashboard, my-leave, my-payslips)                                | Small  |
| WS5.5 | E2E: duplicate invite handled (same email returns existing or deactivates old)                             | Small  |
| WS5.6 | E2E: expired/invalid token shows correct error                                                             | Small  |
| WS5.7 | E2E: registration failure does not burn invitation                                                         | Small  |

**Dependencies**: WS0-WS4

## Execution Order (Updated)

```
WS0 (hardening) ──→ WS1 (seeding) ──→ WS2 (token + leave fixes) ──→ WS3 (invite UI)
                                                                         │
WS4 (landing) ─────────────────────────────────────────────────────────┐ │
                                                                       ↓ ↓
                                                                    WS5 (E2E)
```

- WS0 first (backend fixes that everything else depends on)
- WS1 depends on WS0.5 (unified seed function)
- WS2 depends on WS1 (leave types must exist before creating balances)
- WS3 depends on WS0 + WS2 (company_name in API, token returned)
- WS4 is independent (can start immediately, run in parallel)
- WS5 validates everything

## Deferred (Phase 2)

These are real issues but not blockers for the core onboarding flow:

| Item                                                                    | Why Deferred                                                                       |
| ----------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Email delivery for invites                                              | WhatsApp link-sharing is acceptable for SG SME market MVP                          |
| Leave year-rollover mechanism                                           | Affects employees after 1 year of service; design decision needed on rollover date |
| Annual leave service-year progression (7→14 over 8 years)               | Same as above — coupled with rollover                                              |
| Social proof on landing page (logos, testimonials)                      | Need actual customers first                                                        |
| Employee profile completion for payroll fields (race, DOB, citizenship) | Can be admin-entered via employee edit page which already exists                   |
| Hospitalisation "inclusive of sick leave" relationship                  | Data model enhancement, not blocker                                                |
| Bulk invite UI improvements                                             | Single invites work; CSV import can follow                                         |

## Success Criteria (Updated)

1. New company has 11 leave types (paternity = 28 days), 4 claim categories, attendance settings, and 2026 public holidays immediately after creation
2. Admin invites employee → gets copyable link with company name visible
3. Employee clicks link → sees "[Company Name] invites you as [Role]" → registers → auto-logged in → lands on employee dashboard
4. Duplicate invite for same email is handled (deactivate old, create new)
5. Registration failure does not burn the invitation (rollback works)
6. Employee leave balances respect gender and service month rules
7. Employee self-service pages (my-dashboard, my-leave, my-payslips) display correct data
8. Visitors see ManagementShowcase at root URL with working Sign Up CTA
9. Invalid/expired invite tokens show clear, helpful error messages
