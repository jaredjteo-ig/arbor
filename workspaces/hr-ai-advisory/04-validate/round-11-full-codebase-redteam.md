# Red Team Report: Round 11 — Full Codebase Sweep

**Date**: 2026-04-09
**Agents**: Security Reviewer, Value Auditor, Code Quality Reviewer, Deep Analyst
**Scope**: Entire web codebase + all backend routers

---

## Executive Summary

The platform has converged on security (token versioning, RBAC, PII encryption all verified). This round found **2 critical security issues**, **2 critical feature gaps**, and **11 high/medium UX+quality issues** across the full codebase.

The top 3 to fix:

1. Password change doesn't bump token_version (security — attacker with stolen token survives password change)
2. Cross-tenant alert leak (all companies' escalation alerts visible to all users)
3. Document generation outputs .txt files, not PDF/DOCX (makes contracts unusable)

---

## CRITICAL

### Security

**S-C1: Password change doesn't invalidate sessions**

- File: `src/hr_advisory/api/routers/settings.py:207-209`
- The change_password endpoint updates the hash but does NOT increment `token_version`. If a user changes their password after suspecting compromise, the attacker's old token still works.
- Fix: Add token_version increment + cache invalidation (same pattern as reset_password in auth_service.py)

**S-C2: Cross-tenant escalation alert leak**

- File: `src/hr_advisory/api/routers/alerts.py:265`
- `_alerts_store` is a global list appended to from all companies. The alerts endpoint iterates it without company filtering. All users see all companies' escalation alerts.
- Fix: Add company_id to each alert entry and filter by the requesting user's company

### Feature Gaps

**F-C1: Document generation outputs .txt, not PDF/DOCX**

- Spec: Flow 4 requires PDF and Word downloads
- Reality: `document.py` creates plain text Blobs, frontend downloads as `.txt`
- Impact: Employment contracts as .txt files are unusable

**F-C2: No instant compliance snapshot in company onboarding**

- Spec: Flow 1 Step 3 — "show 3-5 immediate insights" after company setup
- Reality: CompanySetupModal goes Welcome → Form → Success → dashboard reload. No insight step.
- Impact: Missed engagement hook — users don't see immediate value

---

## HIGH

### Security

**S-H1: Unbounded in-memory stores — memory exhaustion**

- `settings.py` — `_user_settings` and `_notification_prefs` grow without bound
- `alerts.py` — `_alert_status` grows without bound
- Fix: Convert to OrderedDict with maxlen eviction

**S-H2: Information leakage via str(exc)**

- `integrations.py`, `admin.py`, `llm_config.py` — internal error messages exposed to clients
- Fix: Use generic messages for infrastructure errors, log originals server-side

### UX

**U-H1: 5 orphan pages unreachable from navigation**

- `/admin` (7-tab operations panel), `/clients`, `/advisory/history`, `/settings/import`, `/settings/notifications`
- Fix: Add sidebar entries or link from existing pages

**U-H2: Dashboard headcount uses wrong field**

- `dashboard/page.tsx:374` reads `employment_type` (full_time/part_time) instead of `pass_type` (citizen/pr/ep/sp/wp)
- Result: All employees show as "Other", named categories show zero

### Code Quality

**Q-H1: N+1 query in employee list — `_bulk_find_users`**

- `employees.py:295-305` — one DB query per user. 200 employees = 200 queries on every page load
- Fix: Single list query with company filter

**Q-H2: Missing math.isfinite() on PayItem amount and recruitment salary**

- `payroll.py:1268` — PayItem amount not validated for NaN/Inf
- `recruitment.py:110-111` — salary_range not validated

### Feature Gaps

**F-H1: S Pass sub-quota not computed in quota calculator**

- `sPassSubDrc` data is defined but never used in calculation or displayed
- Impact: Employers could exceed S Pass sub-quota without warning

**F-H2: Regulatory alert email/push delivery not wired**

- Push service and email adapter exist but never called when alerts are published
- Impact: Users who don't log in regularly miss critical regulatory changes

---

## MEDIUM

| #    | Issue                                                        | Source   | File                                  |
| ---- | ------------------------------------------------------------ | -------- | ------------------------------------- |
| M-1  | Notification bell hardcoded to 0                             | Value    | AppShell.tsx:123                      |
| M-2  | UEN edit contradiction on profile page                       | Value    | profile/page.tsx                      |
| M-3  | 8 pages with zero responsive breakpoints                     | Value    | appraisals, shifts, recruitment, etc. |
| M-4  | CompanySetupModal uses clientsApi instead of profileApi      | Value    | CompanySetupModal.tsx:55              |
| M-5  | Google OAuth lacks rate limiting                             | Security | auth.py:659                           |
| M-6  | Saga tenant isolation type mismatch (str vs int)             | Security | integrations.py:271                   |
| M-7  | datetime.utcnow() used 28 times in onboarding.py             | Quality  | onboarding.py                         |
| M-8  | 13 routers lack rate limiting on write operations            | Quality  | claims, appraisals, shifts, etc.      |
| M-9  | dataflow_crud.count() makes 2 full list queries              | Quality  | dataflow_crud.py:93                   |
| M-10 | Hardcoded limit:10000 as de facto unlimited (21 occurrences) | Quality  | Multiple routers                      |
| M-11 | No what-if scenarios in quota calculator                     | Gaps     | QuotaLevyCalculator.tsx               |

---

## LOW

| #   | Issue                                                | Source   |
| --- | ---------------------------------------------------- | -------- |
| L-1 | Turnover report "Coming Soon" visible                | Value    |
| L-2 | Multilingual "coming soon" for SG languages          | Value    |
| L-3 | Silent error swallowing in dashboard/reports         | Value    |
| L-4 | Two separate headcount sources unsynchronized        | Value    |
| L-5 | Duplicate helper functions across 8 routers          | Quality  |
| L-6 | Document ID uses predictable hash (existence oracle) | Security |

---

## Recommended Fix Order

### Immediate (security + data integrity)

1. **S-C1**: Password change token_version bump (5 min fix)
2. **S-C2**: Alert tenant filtering (15 min fix)
3. **U-H2**: Dashboard headcount field fix (5 min fix)
4. **S-H1**: Bound in-memory stores (15 min fix)
5. **Q-H2**: Add isfinite() checks (5 min fix)

### Next sprint (features + UX)

6. **F-C1**: PDF/DOCX document generation
7. **F-C2**: Compliance snapshot in onboarding
8. **U-H1**: Wire orphan pages into navigation
9. **M-1**: Hook notification bell to alerts API
10. **F-H1**: S Pass sub-quota in calculator

### Backlog

11. Everything else
