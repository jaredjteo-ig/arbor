# Current State Audit: Employee Onboarding & Data Seeding

## Date: 2026-03-18

## Context

AITE has a complete backend for employee invitation-based registration but no frontend page for employees to accept invitations. Additionally, companies are created without essential default operational data (leave types, claim categories, public holidays).

## Backend: Employee Invite Flow (COMPLETE)

### Endpoints

| Endpoint                      | File         | Lines   | Status |
| ----------------------------- | ------------ | ------- | ------ |
| POST /employees/invite        | employees.py | 749-818 | DONE   |
| GET /employees/invite/{token} | employees.py | 826-877 | DONE   |
| POST /auth/register-employee  | auth.py      | 388-620 | DONE   |

### Invitation Model (DB-stored, NOT in-memory)

- `Invitation` model in `company_user.py:1007-1029`
- Fields: company_id, inviter_id, email, role, token, expires_at, accepted_at, is_active
- Indexed on company_id, email, token
- 7-day expiry window
- TOCTOU protection: marks accepted before user creation

### Register-Employee Flow

1. Validates invitation token (exists, not accepted, not expired, email matches)
2. Marks invitation accepted (race condition protection)
3. Creates User via AuthService (role from invitation, company_id set)
4. Creates Employee record (employment_type=full_time, start_date=today)
5. Creates initial LeaveBalance records (Annual=7, Sick=14)
6. Returns JWT tokens

### Token Delivery Gap

- Token is NOT returned in the invite API response (security measure)
- No email delivery mechanism exists
- Admin has no way to get the token to send to employees
- **Decision needed**: Return token in response for MVP, or implement email?

## Frontend: Invite Acceptance (MISSING)

### What Exists

- `/signup` page: standard registration (name, email, password) — no invite token handling
- `/onboarding` page: 4-step post-signup onboarding (Welcome → Company → Compliance → Question)
- Employee self-service pages: `/my-dashboard`, `/my-leave`, `/my-payslips` — all DONE

### What's Missing

- No `/signup?token={token}` or `/invite/{token}` route
- No invite validation UI (show company name, role being offered)
- No invite-specific registration form
- No expired/invalid token error states

## Default Data Seeding

### Currently Auto-Seeded on Company Creation

| Data                      | Seeded? | Where              |
| ------------------------- | ------- | ------------------ |
| CompanyPolicy (4 records) | YES     | profile.py:125-168 |

### NOT Seeded (Must Be Created Manually)

| Data                                    | Defaults Defined?        | Seed Function?                      | Where                  |
| --------------------------------------- | ------------------------ | ----------------------------------- | ---------------------- |
| Leave Type Configs (11 statutory types) | YES                      | YES (`_seed_statutory_leave_types`) | leave.py:229-389       |
| Claim Categories                        | NO                       | NO                                  | Manual only            |
| Attendance Settings                     | YES (hardcoded fallback) | NO                                  | attendance.py:99-117   |
| Public Holidays                         | API-driven (data.gov.sg) | NO                                  | data_gov_sg.py:139-195 |

### Leave Type Defaults Available (11 types)

1. Annual Leave: 7 days (pro-ratable, increases with service)
2. Outpatient Sick Leave: 14 days
3. Hospitalisation Leave: 60 days
4. Maternity Leave: 112 days (female only)
5. Paternity Leave: 14 days (male only)
6. Childcare Leave: 6 days
7. Infant Care Leave: 6 days
8. Adoption Leave: 84 days (female only)
9. Shared Parental Leave: 28 days (male only)
10. Unpaid Infant Care Leave: 6 days
11. NS Reservist Leave: 0 (duration as called, male only)

### Attendance Settings Defaults (inline fallback)

- Work: 09:00-18:00, grace: 15min, OT threshold: 30min
- GPS/photo: disabled
- These work as code defaults but aren't persisted to DB

## Landing Page

### Current Flow

1. Visitor hits `/` → redirected to `/login`
2. Login page: split-screen (ValuePropositionPanel left, form right)
3. No public marketing/landing page exists

### ManagementShowcase

- Defined at `components/management/ManagementShowcase.tsx`
- Rich feature showcase with hero, value props, 8-module feature grid
- Currently UNUSED anywhere in the app
- Could serve as public landing page or pre-company dashboard

## Risk Assessment

| Risk                                           | Severity | Mitigation                             |
| ---------------------------------------------- | -------- | -------------------------------------- |
| Employees cannot register via invite           | CRITICAL | Build invite acceptance page           |
| Companies have no leave types after setup      | HIGH     | Auto-seed on company creation          |
| No claim categories = claims module unusable   | HIGH     | Seed defaults on company creation      |
| No public holidays = leave calendar incomplete | MEDIUM   | Fetch and cache on company creation    |
| No way to deliver invite tokens                | HIGH     | Return token in response for MVP       |
| No public landing page for SEO/marketing       | MEDIUM   | Add ManagementShowcase to public route |
