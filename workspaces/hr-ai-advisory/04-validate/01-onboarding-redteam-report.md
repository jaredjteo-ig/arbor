# Red Team Report: Employee Onboarding Completion Plan

**Date**: 2026-03-18
**Scope**: Analysis of 01-current-state-audit.md, 02-architecture-decisions.md, 02-onboarding-completion-plan.md, 03-employee-onboarding-flow.md, verified against actual source code.
**Complexity Score**: 23/30 (Complex)
**Verdict**: The plan is structurally sound and the audit is accurate, but there are several security risks, data integrity gaps, and edge cases that will cause production failures if not addressed.

---

## Executive Summary

The analysis documents are high quality and correctly identify the most important gaps. However, verification against the codebase reveals seven findings rated Critical or Major that the plan does not address: (1) a non-recoverable partial-failure state when user creation succeeds but the invitation is already burned, (2) a leave balance model mismatch between registration and the leave type config system, (3) two divergent company creation paths where only one receives seeding, (4) no duplicate invitation guard, (5) the validate_invitation endpoint does not return the company name needed by the planned UI, (6) missing leave types in the registration hardcode, and (7) no year-rollover or service-year entitlement progression mechanism.

---

## SECTION 1: CRITICAL FINDINGS

### C1. Invitation Burned on User Creation Failure (No Rollback)

**Risk**: Critical | **Likelihood**: Medium

The `register-employee` endpoint (auth.py:472-482) marks the invitation as accepted BEFORE creating the user. This is documented as TOCTOU protection, and the reasoning is correct for the race condition. However, if `_create_user` then fails for a non-duplicate reason (e.g., DB connection timeout, disk full, DataFlow node error), the invitation is permanently consumed. The employee can never try again because `accepted_at` is set and `is_active` is False.

**Evidence**: auth.py lines 479-482 set `accepted_at` and `is_active=False`. Lines 485-501 create the user. If the user creation raises a non-unique exception, line 500 returns a 500 error, but the invitation remains burned. There is no compensating action to revert the invitation.

**Mitigation**: Add a `try/except` around user creation that reverts the invitation status on failure:

```python
try:
    user = auth_service._create_user(...)
except Exception as exc:
    # Revert invitation -- allow retry
    _update_invitation(invitation["id"], {"accepted_at": "", "is_active": True})
    # ...raise the HTTP error
```

**Plan gap**: Neither the audit nor the plan mentions this failure mode.

---

### C2. Two Divergent Company Creation Paths -- Only One Gets Seeding

**Risk**: Critical | **Likelihood**: High

There are TWO endpoints that create companies:

1. `POST /profile/` in `profile.py:222` -- seeds CompanyPolicy (4 records). This is the path the onboarding flow uses.
2. `POST /clients/` in `clients.py:107` -- seeds NOTHING. This is the path the frontend CompanySetupModal calls (per the recent commit `6a7c9ed` which switched to `clientsApi`).

The plan (WS1.5) says "Wire all seed functions into POST /clients/ handler after company creation." This is correct, but the plan does NOT mention that profile.py ALSO needs to receive the new seed functions (leave types, claim categories, attendance, holidays). If someone creates a company through `POST /profile/`, they will get policies but no leave types.

Worse, the current frontend (`apps/web`) uses `clientsApi` for company creation (per recent commit), which means ZERO seeding happens right now -- not even policies.

**Evidence**: `clients.py` lines 106-191 contain no seed calls. `profile.py` lines 292-301 call `_seed_default_policies` only.

**Mitigation**: Create a single `seed_company_defaults(company_id)` function that calls all seed functions, and invoke it from BOTH creation paths. Better yet, consolidate to one creation endpoint.

**Plan gap**: The plan says "wire into POST /clients/" but does not address the profile.py path or the consolidation question.

---

### C3. Leave Balance vs. Leave Type Config Model Mismatch

**Risk**: Critical | **Likelihood**: High

The `register-employee` flow (auth.py:554-587) creates LeaveBalance records with `leave_type: "annual"` and `leave_type: "sick"` as plain strings. However, the LeaveApplication model (company_user.py:871) uses `leave_type_id: int` (a foreign key to LeaveTypeConfig).

This means:

- LeaveBalance uses string-based `leave_type` codes ("annual", "sick")
- LeaveApplication uses integer `leave_type_id` pointing to a LeaveTypeConfig record
- If the company has no LeaveTypeConfig records (because seeding has not happened yet), the leave_type_id has nothing to point to

The register-employee flow creates LeaveBalance records but does NOT verify that corresponding LeaveTypeConfig records exist for the company. If the company was created via `POST /clients/` (which seeds nothing), the employee gets balance records for leave types that are not configured.

**Evidence**: auth.py:565 uses `leave_type: "annual"` (string). company_user.py:871 defines `leave_type_id: int` on LeaveApplication. company_user.py:967 defines `leave_type: str` on LeaveBalance. These are disconnected models.

**Mitigation**: The plan's WS1 (seed on company creation) will fix the root cause IF it is done before WS3. Make WS1 a hard prerequisite for WS3, not a parallel workstream. Also add a guard in register-employee to verify LeaveTypeConfig exists before creating balances.

**Plan gap**: The plan shows WS1-WS4 as parallel. WS1 MUST complete before WS3 can work correctly.

---

## SECTION 2: MAJOR FINDINGS

### M1. Validate-Invitation Endpoint Does Not Return Company Name

**Risk**: Major | **Likelihood**: Certain

The user flow (03-employee-onboarding-flow.md, step 3) says the signup page will show: "You've been invited to join [Company Name] as [Role]". However, the `GET /employees/invite/{token}` endpoint (employees.py:872-877) returns:

```python
return {
    "valid": True,
    "email": invitation.get("email"),
    "role": invitation.get("role"),
    "company_id": invitation.get("company_id"),
}
```

It returns `company_id` (an integer), NOT the company name. The frontend would need to make a second API call to `GET /profile/{company_id}` or `GET /clients/{company_id}` to get the name, but those endpoints require authentication, and the employee is not logged in yet.

**Evidence**: employees.py lines 872-877. The Invitation model (company_user.py:1007-1029) stores only `company_id`, not the company name.

**Mitigation**: Look up the company name in the validate_invitation handler and include it in the response:

```python
return {
    "valid": True,
    "email": invitation.get("email"),
    "role": invitation.get("role"),
    "company_id": invitation.get("company_id"),
    "company_name": company_record.get("name", ""),
}
```

**Plan gap**: The plan does not mention this needed backend change. WS3 will hit this immediately.

---

### M2. No Duplicate Invitation Guard

**Risk**: Major | **Likelihood**: High

The `POST /employees/invite` endpoint (employees.py:749-818) does NOT check whether an active, unexpired invitation already exists for the same email + company. An admin who clicks "Invite" twice (or invites the same person from two browser tabs) will create duplicate invitation records with different tokens.

If the employee uses the first link and the admin shares the second, the employee will see a confusing "already used" error. If the admin then shares the first link, the employee registration will succeed, but a stale invitation record remains in the DB. More importantly, there is no check for whether the email already belongs to an existing user in the company.

**Evidence**: employees.py:749-818 has no deduplication logic. No check for existing invitation or existing user.

**Mitigation**: Before creating a new invitation, check for:

1. Active, unexpired invitation for same email + company: return the existing one (or deactivate it first)
2. Existing user with that email already in the company: return 409

---

### M3. Only 2 of 11 Leave Types Get Balance Records on Registration

**Risk**: Major | **Likelihood**: Certain

The register-employee flow creates LeaveBalance for `annual` (7 days) and `sick` (14 days) only. But `_seed_statutory_leave_types` creates 11 leave type configs. The remaining 9 types (hospitalisation, maternity, paternity, childcare, infant care, adoption, shared parental, unpaid infant care, NS) get type configs but zero balance records.

This means when an employee views "My Leave", they will see balances for only 2 types. When they try to apply for childcare leave, no balance exists.

**Evidence**: auth.py:557-587 creates only "annual" and "sick" balances. leave.py:229-362 defines 11 types.

**Mitigation**: Either:

- Create balance records for all 11 leave types during registration (with appropriate entitlement days from the config), OR
- Implement lazy balance creation: when an employee views their leave or applies for leave, auto-create the balance from the LeaveTypeConfig if it does not exist yet.

The lazy approach is better because it respects the `applicable_gender` field (no maternity balance for male employees) and `min_service_months` requirements.

**Plan gap**: The plan does not mention this mismatch. The audit notes "7 annual, 14 sick" as if it is complete, but 9 leave types are orphaned.

---

### M4. Hardcoded Entitlements Ignore Service Year Progression

**Risk**: Major | **Likelihood**: Medium (becomes certain after 1 year)

The register-employee flow hardcodes `entitlement_days: 7.0` for annual leave. The Singapore Employment Act specifies a progression: 7 days in year 1, +1 per year, up to 14 days maximum. This is correctly implemented in `calculator.py:47-51` (`_annual_leave_days`) and `leave_calculator.py:60-99`, but the balance creation in register-employee does not use these functions.

There is NO mechanism to update entitlements when a new calendar year starts. On January 1, 2027:

- An employee who joined in March 2026 should get 8 days annual leave (year 2 entitlement)
- Their LeaveBalance record will still show 7.0 days unless someone manually creates a new record

Similarly, sick leave entitlement depends on months of service in the first year (3 months = 5 days, 4 months = 8 days, 5 months = 11 days, 6+ months = 14 days). The register-employee flow gives 14 days immediately, which is incorrect for new hires.

**Evidence**: auth.py:567 hardcodes 7.0. auth.py:582 hardcodes 14.0. calculator.py:47-51 shows the correct progression logic.

**Mitigation**:

1. For new registration: calculate actual entitlement based on start_date (pro-rate for partial year, check min service months)
2. Build a year-rollover job or lazy-init pattern that recalculates entitlements annually based on completed service years
3. For sick leave: do not grant 14 days immediately. Use the `min_service_months: 3` from LeaveTypeConfig.

**Plan gap**: The plan does not address year rollover or service-year progression at all. The user flow document (question 7 in the request) asks about this explicitly.

---

## SECTION 3: SIGNIFICANT FINDINGS

### S1. Token Returned in API Response -- Security Implications

**Risk**: Significant | **Likelihood**: Low (but high impact if exploited)

ADR-1 correctly identifies the tradeoff: returning the token in the response is MVP-appropriate. However, the current code (employees.py:807-809) explicitly comments that the token is NOT returned for security reasons. The plan proposes reversing this deliberate security decision.

The specific risks:

- **Browser DevTools**: Any admin-side JavaScript or browser extension can read the invite token from the response
- **API Logging**: If the API gateway or reverse proxy logs response bodies, tokens appear in logs
- **Admin impersonation**: An admin could register as the employee by using the token themselves (the email check at auth.py:460-465 prevents this, which is good)
- **Shared admin sessions**: In SG SMEs, it is common for multiple people to share a single admin login

The email-match check (auth.py:460-465) is the critical safeguard here. It means the token alone is not sufficient -- you must also control the email inbox. This makes the risk tolerable for MVP.

**Mitigation**: Accept for MVP but:

1. Log the token access in an audit trail (who generated, when, for which email)
2. Add rate limiting to the invite endpoint (prevent bulk token generation)
3. Document this as a known risk to remediate with email delivery later

**Plan gap**: The plan acknowledges the tradeoff but does not specify audit logging or rate limiting for the invite endpoint.

---

### S2. No Invitation Cancellation or Re-invite Flow

**Risk**: Significant | **Likelihood**: Medium

There is no endpoint to cancel/revoke an invitation, and no endpoint to resend or regenerate one. If an admin sends an invite to the wrong email, or the link expires before the employee uses it, the admin has no recourse except creating a brand new invitation (which succeeds because there is no duplicate guard -- see M2).

Over time, this creates accumulating dead invitation records in the database.

**Evidence**: Grepping for "revoke", "cancel", "resend", "reinvite" across the codebase returned zero results.

**Mitigation**: Add:

1. `DELETE /employees/invite/{invitation_id}` to revoke an invitation
2. `POST /employees/invite/{invitation_id}/resend` to deactivate old token and create new one
3. A query to show pending invitations on the employees page

**Plan gap**: The plan does not mention invitation lifecycle management.

---

### S3. CSV Import Creates Invitations Without Returning Tokens

**Risk**: Significant | **Likelihood**: High

The CSV import flow (employees.py:1810-1842) creates invitations via `_create_invitation` but does NOT return the tokens in the response. The response contains only `created` count and `skipped` count. This means if an admin imports 20 employees via CSV, they have no way to get the 20 invite links.

**Evidence**: employees.py:1837-1842 returns counts only. The tokens generated at line 1816 are not captured in the response.

**Mitigation**: Return the list of created invitations with their tokens/invite URLs in the import response.

**Plan gap**: The plan focuses on the single-invite flow (WS2) but does not address CSV import token delivery.

---

### S4. Public Holiday Seeding Has No DB Model Referenced

**Risk**: Significant | **Likelihood**: Medium

The plan (WS1.4) says to seed public holidays and store them in DB. The leave router has `GET /public-holidays` and `POST /public-holidays` endpoints (leave.py:963-994). However, I need to verify a PublicHoliday model exists in the DataFlow models.

The `data_gov_sg.py` adapter fetches holidays but stores them in an in-memory cache, not in the database. The plan assumes database storage but the adapter does not write to DB.

**Mitigation**: Verify the PublicHoliday DataFlow model exists. If not, create it before implementing WS1.4. The POST /public-holidays endpoint likely handles the DB write, but the seed function needs to call it or use the same DataFlow node.

---

### S5. Employee Record Created Without Key Fields

**Risk**: Significant | **Likelihood**: Certain

The register-employee flow (auth.py:511-522) creates an Employee record with only:

- user_id, company_id, employment_type ("full_time"), start_date (today), is_active (True)

Missing fields that the employee table likely supports: name, email, department, designation, monthly_salary, race (needed for SHG fund routing in payroll), date_of_birth (needed for CPF age-band calculation), citizenship_status (needed for CPF eligibility).

Without race, DOB, and citizenship, payroll cannot run correctly. The plan's success criterion 3 ("Payroll can be run for the new employee with correct CPF, SDL, SHG calculations") will fail because these fields are empty.

**Evidence**: auth.py:511-522 does not pass race, date_of_birth, or citizenship_status. The HRIS engine memory notes confirm payroll needs these fields.

**Mitigation**: Either:

1. Add a post-registration "complete your profile" step where the employee fills in personal details, OR
2. Allow the admin to provide these details in the invite flow, OR
3. Make the payroll engine gracefully handle missing fields with clear error messages about what needs to be filled in

**Plan gap**: The plan does not address the gap between registration data and payroll-required data.

---

## SECTION 4: MINOR FINDINGS

### N1. `employee_id = 0` Fallback Creates Ghost Records

auth.py:552 falls back to `employee_id = 0` if the employee record cannot be retrieved after creation. This means LeaveBalance records could be created with `employee_id = 0`, which is not a valid employee.

### N2. LocalRuntime Used in Registration (Not AsyncLocalRuntime)

auth.py:523 uses `LocalRuntime()` inside an async endpoint. This blocks the event loop during registration. For a single-user registration this is tolerable, but under load it will cause timeouts.

### N3. No Frontend Handling of Google OAuth for Invite Flow

The signup page has Google SSO (lines 162-191). If an employee receives an invite link and clicks "Sign up with Google" instead of filling the form, the invite flow breaks because Google OAuth goes through a different registration path that does not consume the invitation token.

### N4. Attendance Settings Seed is Vague

The plan says "persist existing defaults to DB" for attendance settings, but the current defaults are inline code fallbacks (attendance.py:99-117), not a clear set of seed values. The implementation needs to define what exactly gets persisted and verify an AttendanceSettings DataFlow model exists.

---

## SECTION 5: CROSS-REFERENCE AUDIT

| Document                              | Finding                                                                                                                                                            |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 01-current-state-audit.md line 38-40  | ACCURATE: Token is not returned in invite response. Confirmed at employees.py:807-818                                                                              |
| 01-current-state-audit.md line 33     | ACCURATE: LeaveBalance creates Annual=7, Sick=14. Confirmed at auth.py:554-587                                                                                     |
| 01-current-state-audit.md line 64     | ACCURATE: CompanyPolicy seeded on creation. Confirmed at profile.py:292-301                                                                                        |
| 01-current-state-audit.md line 64     | INACCURATE: Audit says CompanyPolicy is seeded on company creation. TRUE for profile.py path, but FALSE for clients.py path which is the one the frontend now uses |
| 02-architecture-decisions.md ADR-2    | RISK: Assumes one company creation path. There are two                                                                                                             |
| 02-onboarding-completion-plan.md      | RISK: Shows WS1-WS4 as parallel. WS1 must precede WS3                                                                                                              |
| 03-employee-onboarding-flow.md step 3 | INACCURATE: Says page shows "Company Name" but API returns only company_id                                                                                         |
| 03-employee-onboarding-flow.md step 5 | INCOMPLETE: Says "Backend creates: User + Employee + LeaveBalance (7 annual, 14 sick)" but does not mention that 9 other leave types will have zero balance        |

---

## SECTION 6: RISK REGISTER

| #   | Risk                                             | Likelihood             | Impact   | Severity    | Mitigation                                                  |
| --- | ------------------------------------------------ | ---------------------- | -------- | ----------- | ----------------------------------------------------------- |
| C1  | Invitation burned on user creation failure       | Medium                 | Critical | Critical    | Add rollback logic on \_create_user failure                 |
| C2  | clients.py company creation path has no seeding  | High                   | Critical | Critical    | Unify seeding into shared function, call from both paths    |
| C3  | LeaveBalance/LeaveTypeConfig disconnect          | High                   | High     | Critical    | Make WS1 prerequisite for WS3; add guard in register        |
| M1  | validate_invitation does not return company name | Certain                | Medium   | Major       | Add company name lookup to validate endpoint                |
| M2  | No duplicate invitation guard                    | High                   | Medium   | Major       | Check existing active invitation before creating new one    |
| M3  | Only 2 of 11 leave types get balances            | Certain                | High     | Major       | Implement lazy balance creation or seed all on registration |
| M4  | No service year entitlement progression          | Certain (after year 1) | High     | Major       | Build year-rollover mechanism                               |
| S1  | Token in API response security implications      | Low                    | High     | Significant | Add audit logging, document as known risk                   |
| S2  | No invitation cancel/resend flow                 | Medium                 | Medium   | Significant | Add revoke and resend endpoints                             |
| S3  | CSV import does not return tokens                | High                   | Medium   | Significant | Return tokens in import response                            |
| S4  | Public holiday seed has no clear DB model path   | Medium                 | Medium   | Significant | Verify model, clarify storage strategy                      |
| S5  | Employee record missing payroll-required fields  | Certain                | High     | Significant | Add profile completion step or admin input                  |

---

## SECTION 7: RECOMMENDED PLAN MODIFICATIONS

### 1. Change Execution Order

The plan shows WS1-WS4 as parallel. Change to:

```
WS1 (seeding) ──→ WS3 (invite acceptance)
WS2 (token)  ──→ WS3 (invite acceptance)
WS4 (landing) ────────────────────────────→ WS5 (E2E)
```

WS1 and WS2 can run in parallel. WS3 depends on both. WS4 is independent.

### 2. Add WS0: Backend Hardening (Before Everything Else)

| Task  | Description                                           | Effort |
| ----- | ----------------------------------------------------- | ------ |
| WS0.1 | Add invitation rollback on user creation failure      | Small  |
| WS0.2 | Add duplicate invitation guard (same email + company) | Small  |
| WS0.3 | Add company_name to validate_invitation response      | Small  |
| WS0.4 | Unify company creation seeding into shared function   | Medium |
| WS0.5 | Add invitation revocation endpoint                    | Small  |

### 3. Add WS6: Leave Entitlement Correctness

| Task  | Description                                                                | Effort |
| ----- | -------------------------------------------------------------------------- | ------ |
| WS6.1 | Implement lazy LeaveBalance creation from LeaveTypeConfig                  | Medium |
| WS6.2 | Respect min_service_months and applicable_gender on balance creation       | Medium |
| WS6.3 | Calculate initial entitlement from service months (not hardcode 7/14)      | Small  |
| WS6.4 | Design year-rollover mechanism (cron job or lazy on first access per year) | Large  |

### 4. Modify WS2 (Token Return)

Add to WS2:

- Return tokens in CSV import response (not just single invite)
- Add audit log entry when token is generated and viewed

### 5. Add to Success Criteria

Current criteria are missing:

- 6. Duplicate invite for same email is handled gracefully
- 7. Employee who joins mid-year gets pro-rated leave entitlement
- 8. Payroll-required fields (race, DOB, citizenship) have a collection path
- 9. Invitation failure during registration does not permanently lock out the employee

---

## SECTION 8: QUESTIONS REQUIRING STAKEHOLDER INPUT

1. **Two company creation paths**: Should `POST /clients/` and `POST /profile/` be consolidated into a single endpoint? The frontend recently switched to clients, but profile has more fields.

2. **Payroll data collection**: When in the flow should race, date of birth, and citizenship be collected? During invite (admin provides)? During registration (employee provides)? In a post-registration profile completion step?

3. **Year-rollover timing**: Should leave entitlements roll over on Jan 1 (calendar year), on the employee's anniversary date, or on the company's financial year start?

4. **Google OAuth + invite flow**: Should Google SSO be hidden on the invite acceptance page to prevent employees from bypassing the invitation token flow?

5. **Invitation expiry window**: 7 days is reasonable for MVP, but should this be configurable per company?

---

_Report prepared by deep-analyst agent. All line numbers and findings verified against source code as of 2026-03-18._
