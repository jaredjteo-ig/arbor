# Red Team Findings: Consolidated

## Date: 2026-03-18

## Sources

- Deep-analyst: Technical gaps, security risks, edge cases
- Value-auditor: Enterprise buyer perspective, UX friction, market fit

## CRITICAL (Must fix before shipping)

### 1. Paternity Leave Seeded at 14 Days Instead of 28

**Source**: Value auditor
**Location**: leave.py:283
**Issue**: CDCSA amendment effective January 1, 2025 doubled paternity leave from 2 weeks (14 days) to 4 weeks (28 days). The knowledge base (`templates/content.py:133`) has the correct value but the seed function does not.
**Impact**: Every male employee gets wrong leave balance from day one. Destroys the "Singapore Compliant" credibility.
**Fix**: Single-line change from `14.0` to `28.0`.

### 2. Two Divergent Company Creation Paths

**Source**: Deep-analyst (C2)
**Issue**: `POST /clients/` (used by frontend CompanySetupModal since commit `6a7c9ed`) seeds NOTHING. `POST /profile/` seeds only CompanyPolicy. The plan says "wire into POST /clients/" but doesn't address profile.py or consolidation.
**Impact**: Companies created via the current frontend get zero default data.
**Fix**: Create single `seed_company_defaults(company_id)` function, call from both paths.

### 3. Invitation Burned on User Creation Failure

**Source**: Deep-analyst (C1)
**Location**: auth.py:479-501
**Issue**: Invitation marked as accepted BEFORE user creation. If user creation fails (DB timeout, etc.), invitation is permanently consumed. Employee locked out forever.
**Fix**: Wrap user creation in try/except, revert invitation on failure.

### 4. LeaveBalance/LeaveTypeConfig Model Disconnect

**Source**: Deep-analyst (C3)
**Issue**: register-employee creates LeaveBalance records (string-based `leave_type`) but LeaveApplication uses `leave_type_id` (FK to LeaveTypeConfig). If no LeaveTypeConfig exists, the leave system is broken.
**Impact**: WS1 (seeding) MUST complete before WS3 (invite acceptance). They cannot be parallel.

## HIGH (Must address in this sprint)

### 5. validate_invitation Returns company_id, Not company_name

**Source**: Both red teams (M1)
**Issue**: Frontend needs to show "You've been invited to join [Company Name]" but endpoint returns an integer ID. Employee is not authenticated, can't call other APIs.
**Fix**: Look up company name in validate handler, include in response.

### 6. Only 2 of 11 Leave Types Get Balance Records

**Source**: Deep-analyst (M3)
**Issue**: register-employee creates balances for annual (7) and sick (14) only. Nine other statutory leave types get zero balance.
**Fix**: Implement lazy balance creation from LeaveTypeConfig, respecting applicable_gender and min_service_months.

### 7. Employee Record Missing Payroll-Required Fields

**Source**: Deep-analyst (S5)
**Issue**: Employee created with only user_id, company_id, employment_type, start_date, is_active. Missing: race (SHG), DOB (CPF age band), citizenship_status (CPF eligibility), monthly_salary.
**Impact**: Payroll cannot run correctly without these fields.
**Fix**: Add post-registration profile completion step, or allow admin to provide in invite.

### 8. No Duplicate Invitation Guard

**Source**: Deep-analyst (M2)
**Issue**: Admin can create unlimited invitations for the same email. No check for existing active invitation or existing user.
**Fix**: Check before creating; deactivate old invitation if exists.

### 9. Sick Leave 14 Days Violates min_service_months: 3

**Source**: Deep-analyst (M4)
**Issue**: New hires get 14 sick leave days immediately, but EA specifies progressive entitlement (5 days at 3 months, 8 at 4, 11 at 5, 14 at 6+).
**Fix**: Calculate initial entitlement from service months.

## MEDIUM (Should address, can follow-up)

### 10. ManagementShowcase CTA Assumes Authenticated State

**Source**: Value auditor
**Issue**: Component opens CompanySetupModal on click, which needs auth. Public landing page visitors will get errors.
**Fix**: CTA links to /signup on public page.

### 11. Signup ValuePropositionPanel Shows Advisory Messaging

**Source**: Value auditor
**Issue**: Panel shows "AI-Powered HR Compliance" (advisory), not "Complete HR Management Suite" (HRIS). Invite flow employees see irrelevant messaging.
**Fix**: Update panel or create invite-specific variant.

### 12. CSV Import Doesn't Return Tokens

**Source**: Deep-analyst (S3)
**Issue**: Bulk import creates invitations but doesn't return tokens.
**Fix**: Return invite URLs in import response.

### 13. No Invitation Lifecycle Management

**Source**: Deep-analyst (S2)
**Issue**: No cancel, revoke, or resend endpoints. No pending invitations list for admin.
**Fix**: Add revocation endpoint and UI table.

### 14. Google OAuth Bypasses Invite Flow

**Source**: Deep-analyst (N3)
**Issue**: If employee clicks "Sign up with Google" on invite page, invitation token is not consumed.
**Fix**: Hide Google SSO on invite acceptance, or wire it through invite flow.

## Stakeholder Questions

1. Should `POST /clients/` and `POST /profile/` be consolidated into one endpoint?
2. When should payroll-required fields (race, DOB, citizenship) be collected?
3. Should leave entitlements roll over on Jan 1, anniversary date, or financial year?
4. Should invitation expiry (7 days) be configurable per company?
