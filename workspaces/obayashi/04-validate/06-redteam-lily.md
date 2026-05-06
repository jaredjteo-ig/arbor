# Round-7 Redteam — Lily Phang Employee Walkthrough

**Date**: 2026-05-06
**Live target**: http://136.110.51.61/ (commit `d734d3d`)
**Account**: Lily Phang (employee, role=`employee`) — `lily.phang@central-solutions.sg`
**Method**: Playwright MCP, every page she has access to, every primary action attempted end-to-end.

## Pages walked + happy-path verdict

| Page             | Loaded | Primary action verdict                                                                                                                                                                                                                                                                                                                                           |
| ---------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/my-dashboard`  | ✅     | Read-only summary, content correct                                                                                                                                                                                                                                                                                                                               |
| `/my-onboarding` | ✅     | ❌ Says "no tasks assigned" but Grace's view shows Lily 100% complete on `HR Technology / SaaS Onboarding` — contract mismatch                                                                                                                                                                                                                                   |
| `/my-profile`    | ✅     | 🔴 Save returns 200 + `{updated: true, fields: ["alias", ...]}` — but reload shows `alias: ""`; backend lies about persisting                                                                                                                                                                                                                                    |
| `/my-leave`      | ✅     | ✅ Submitted Annual Leave 12-13 May → 200, application appears in history with status pending                                                                                                                                                                                                                                                                    |
| `/my-claims`     | ✅     | 🔴 Submit Claim button stays disabled, no clear path to add expense items, no validation message; submit silently does nothing                                                                                                                                                                                                                                   |
| `/my-payslips`   | ✅     | ⚠️ Expand reveals only Gross / EE CPF / ER CPF / Net (no allowances, no SDL, no leave taken, no PDF download). Background fetch fires `GET /api/payroll/my-payslips/undefined` → 422                                                                                                                                                                             |
| `/my-attendance` | ✅     | ✅ Clock-in worked, history populated. ⚠️ Status auto-tagged "late" without any shift template defined for Lily — looks broken                                                                                                                                                                                                                                   |
| `/my-timesheets` | ✅     | ❌ Project dropdown empty (Lily not assigned to any project), so she literally cannot log time. Empty state text ("Start logging hours against your projects") is misleading                                                                                                                                                                                     |
| `/my-inventory`  | ✅     | 🔴 Submit Request → **HTTP 500 Internal Server Error** ("A server error occurred. Please try again later."). Backend crash on `/api/inventory/requests`                                                                                                                                                                                                          |
| `/advisory`      | ✅     | 🔴 Asked "Can my employer delay my CPF contribution?" → "I'm having trouble processing your question right now. Please try again in a moment." Response card stamped _High Risk — Action Required, Low confidence_. Advisor is broken for Lily. Also: history shows Grace's HR-manager queries (privacy concern) and suggested questions are HR-manager-oriented |
| `/settings`      | ✅     | Functional. Minor inconsistency in AI Memory observed-paths labels                                                                                                                                                                                                                                                                                               |
| `/help`          | ✅     | Help content is entirely HR-manager oriented — every "next step" she's told to take points to admin-only pages she can't access                                                                                                                                                                                                                                  |

## 🔴 HIGH severity

### H1. `/my-inventory` request returns 500

- Filled the textarea, clicked Submit Request → `POST /api/inventory/requests` returned `500 Internal Server Error` body `Internal Server Error`. Toast: "A server error occurred. Please try again later."
- Reproducible. Means the asset-request flow is fully broken for employees on prod.
- **Action**: read backend logs for the stack trace; the helper rewrite in earlier rounds may have introduced it (we touched `inventory.list_item_requests`, but a `create_item_request` path may now reference a removed import or expect a field the frontend isn't sending).

### H2. `/my-profile` Save lies about persisting

- PUT `/api/employees/me` returns `{updated: true, fields: ["name", "alias", "date_of_birth", "gender", "race", "nationality", "religion", "marital_status"]}` with status 200.
- Subsequent GET `/api/employees/me` returns the row with `alias: ""` (and presumably the other "updated" fields are also unchanged, untested).
- The Employee model on the backend likely has no `alias` column (or the column is in `User`, not `Employee`), so the PUT silently drops the field. The response body is the bug — it claims the field updated when nothing was written.
- **Action**: verify `Employee.alias` exists in the model or move the field to `User`. Either way, the response should not lie.

### H3. `/advisory` is broken

- Lily asked "Can my employer delay my CPF contribution?" — got a generic "I'm having trouble processing your question right now" with a `High Risk — Action Required` red banner. No actual answer. The whole reason the platform exists doesn't work for her.
- Backend likely returned an error from the LLM call or the safety chain rejected; either way the user-facing copy is "try again" with no diagnosis.
- **Action**: pull the backend logs for `/api/advisory/...`; this may be model misconfiguration, an LLM provider error, or a safety-chain false-positive.

### H4. `/my-claims` Submit button silently disabled, no path to add items

- The form opens with one inline expense-item row (Category select + Description text input + Amount + per-item Date), but the Submit Claim button is `disabled` from the start.
- Filling the visible inputs via React-controlled state (synthetic events) didn't enable the button. There's no "+ Add another item" affordance, no inline validation message, and no help text explaining what's missing.
- A real user would conclude "this form is broken" and walk away. Whether the bug is in client-side form state or in a hidden required field, the UX is failing.
- **Action**: walk the form code path (`apps/web/src/app/(dashboard)/my-claims/page.tsx`) — the disabled-submit guard is too eager / ambiguous.

## ⚠️ MEDIUM severity

### M1. `/my-onboarding` shows empty for Lily despite Grace's view

- Grace's `/employees` Onboarding tab earlier in this session showed "Lily Phang · HR Technology / SaaS Onboarding · 100% Completed".
- Lily's own `/my-onboarding` says "No onboarding tasks assigned". Either the assignment is keyed by a different ID or `/api/onboarding/me` looks at the wrong scope.

### M2. `/my-payslips` `GET /api/payroll/my-payslips/undefined` → 422

- Visible expand of a payslip row works but a stray fetch fires with `undefined` as the id segment. Not user-visible but pollutes prod logs.

### M3. `/my-payslips` detail too sparse

- Expanded payslip shows only Gross / EE CPF / ER CPF / Net — no allowances breakdown, no SDL/SHG, no working days, no PDF download. A normal employee will want to see "Why is my salary $X this month?"

### M4. `/my-claims` description is single-line

- The expense item description is `<input type=text>`. Real expenses ("Client lunch + cab + tip — Din Tai Fung Vivo, met Mr. Tan from Acme") need a textarea.

### M5. `/my-timesheets` blocks employees with no project assignment

- Project dropdown only contains "Select project" because Lily isn't on any of the company's 2 projects. The form is therefore unusable. Either the empty state should be "You're not assigned to any project — ask your manager to add you" or the form should be hidden.

### M6. `/advisory` history shows Grace's questions

- Lily can see "What leave entitlements do my employees have?" / "How do I calculate CPF contributions?" / "What are the foreign worker quota limits for my sector?" — questions an HR-manager (not an employee) would ask. Either history should be per-user, or the suggestion list should be role-aware.

### M7. `/advisory` suggested questions are HR-manager-oriented

- Suggestions to Lily: "What leave entitlements do my employees have?" / "How do I calculate CPF contributions?" / "Am I compliant with the Employment Act?" / "What are the foreign worker quota limits for my sector?" / "How do I handle a resignation properly?"
- For an employee, none of these apply. Should be: "What's my CPF contribution this month?", "How do I apply for shared parental leave?", "Can my employer change my notice period?".

### M8. `/help` is admin-only content

- Every item on /help points to admin-gated pages — "Set up your company profile", "Run a compliance check", "Use the calculators", "Check regulatory alerts", "Know where to go in an emergency". Lily can do almost none of these. Help should role-branch.

### M9. Compliance warnings shown on every page footer for employees

- "Key Employment Terms (KET) not issued to employees" / "No overtime records maintained" / "No formal grievance handling process" / "Foreign workers employed — ensure all passes are valid and conditions are met" / "Updated CPF contribution rates for 2026" appear on every page including Lily's. These are HR-manager findings — Lily can't act on them.

### M10. Attendance auto-status "late" without any shift defined

- Clock-in at 5:52pm SGT was tagged `status: "late"`. Lily has no shift template assigned, so "late" is meaningless. Should default to "present" when no shift is configured.

## 🟡 LOW severity

### L1. `/api/alerts/unread-count` returns 403 to employees

- Console error fires on every page load: "Failed to load resource: the server responded with a status of 403 (Forbidden)" for `/api/alerts/unread-count`. Endpoint is admin-gated; frontend should not call it for employees, OR backend should return `{count: 0}` for non-admins.

### L2. Profile employment_type renders raw enum

- `/my-profile` Employment Type field shows `full_time` (raw enum value). Should be "Full-Time".

### L3. Profile dates render ISO instead of human format

- Start Date shows `2023-05-01` on profile; dashboard shows "1 May 2023". Pick one.

### L4. Annual Leave entitlement changed mid-session

- Dashboard initially showed "Annual Leave: 7 remaining". After applying for 1-day leave, the balance recomputed to 9 entitlement, 1 pending, 8 remaining. Either dashboard was stale or pro-ration recalculated on submit. Should be consistent.

### L5. Settings AI Memory observed-paths inconsistency

- Half the entries show humanized labels ("My Dashboard", "My Leave") and half show raw paths ("/my-profile", "/my-onboarding", "/my-claims"). Inconsistent.

## 🟢 Verified working

- Login flow + session persistence ✓
- `/my-leave` — filed an Annual Leave application 12-13 May, success toast, application appears in history with `pending` status, balance updated ✓
- `/my-attendance` clock-in — POST 200, history table populated ✓
- `/my-profile` — fields load correctly, NRIC/bank account masked correctly ✓
- `/my-payslips` — April 2026 payslip card loads, click expands inline ✓
- `/settings` — full set of preferences (notifications, language, theme, AI memory, PDPA export/delete) ✓
- Activity feed click-through (HR-only, but verified Grace earlier this round) ✓
- Round-3+5 enrichment changes still hold (no `Employee #N` anywhere on Lily's surfaces) ✓

## Recommended fix order

1. **H1 inventory 500** — backend crash on a primary employee action; investigate logs first
2. **H3 advisory broken** — the platform's tagline feature is non-functional for employees
3. **H4 my-claims silently disabled submit** — submit-or-bust UX is a deal-breaker
4. **H2 profile save lies** — return-body should reflect actual persistence; remove `alias` from accepted-fields list if column doesn't exist
5. **M5 timesheets empty project list** — show actionable empty state
6. **M1 onboarding contract mismatch** — Lily should see her own onboarding completion
7. **M9 compliance warnings on employee pages** — gate to admins
8. **M6/M7/M8 advisory + help role mismatch** — branch by role
9. The L-tier polish items (raw enum, ISO date, paths label inconsistency)

## Test artefacts

- Leave application created: id `13`, employee_id `28` (Lily), status `pending`, 12-13 May 2026, 1 day, reason "Red-team smoke — short break"
- Attendance record created: id `2`, clock_in `2026-05-06T09:52:17 UTC`, status `late`
- One stray Profile PUT was issued ("RedteamAlias2") — backend claimed updated, GET shows empty
- Inventory POST attempted with body "Red-team smoke — second monitor for home office" — failed 500
