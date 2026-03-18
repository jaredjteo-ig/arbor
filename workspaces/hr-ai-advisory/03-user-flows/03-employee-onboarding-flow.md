# User Flow: Employee Onboarding (End-to-End)

## Flow 1: New Visitor → Company Owner

```
1. Visitor lands on https://aite.kailash.ai/
   → Sees ManagementShowcase (public landing page)
   → Hero: "Your Complete HR Management Suite"
   → Value props: Free, AI-Powered, Singapore Compliant, All-in-One
   → 8 module feature cards with capabilities
   → CTA: "Get Started Free" → /signup

2. Visitor clicks "Get Started Free"
   → /signup page (standard registration)
   → Enters: name, email, password
   → Submits → POST /auth/register
   → Auto-login → redirect to /dashboard

3. Dashboard (no company)
   → Greeting: "Welcome, [Name]"
   → "Set Up Company" CTA prominently displayed
   → HRISModuleGrid showing 11 modules (all link to setup)
   → Getting Started steps

4. User clicks "Set Up Company"
   → CompanySetupModal opens (3 steps)
   → Step 1: Welcome (explains benefits)
   → Step 2: Form (company name, UEN, sector, headcount)
   → Step 3: Success confirmation

5. Company created → AUTOMATIC SEEDING:
   → 4 company policies (leave, FWA, handbook, WSH)
   → 11 statutory leave types (annual, sick, maternity, etc.)
   → 4 claim categories (transport, meals, medical, office supplies)
   → Attendance settings (09:00-18:00, 15min grace)
   → 2026 public holidays (from data.gov.sg)

6. Page reloads → Dashboard (with company)
   → Living briefing card
   → Compliance score, pending actions
   → All modules now active and navigable
```

## Flow 2: Admin Invites Employee

```
1. Admin navigates to /employees
   → Sees employee roster (initially empty)
   → Clicks "Invite Employee"

2. Invite modal opens
   → Admin enters: employee email, role (employee/hr_manager)
   → Optionally: designation, department, monthly salary
   → Submits → POST /employees/invite

3. Response returns invite_url
   → Modal shows: "Invitation sent!"
   → Copyable invite link displayed
   → Admin copies link → shares via WhatsApp/email/etc.
```

## Flow 3: Employee Accepts Invite

```
1. Employee clicks invite link
   → https://aite.kailash.ai/signup?token=abc123

2. Signup page detects token parameter
   → Calls GET /employees/invite/{token}
   → Validates: exists, not expired, not used

3. If VALID:
   → Banner: "You've been invited to join [Company Name] as [Role]"
   → Email pre-filled (read-only, from invitation)
   → Form shows: name, password, confirm password
   → Submit button: "Accept Invitation & Create Account"

4. If INVALID/EXPIRED:
   → Error message: "This invitation is invalid or has expired."
   → "Contact your employer for a new invitation link."
   → Link to standard signup still available

5. Employee submits form
   → POST /auth/register-employee {name, email, password, invitation_token}
   → Backend creates: User + Employee + LeaveBalance (7 annual, 14 sick)
   → Returns JWT tokens

6. Auto-login → redirect to /my-dashboard
   → Employee sees: employment summary, leave balances, quick actions
   → Sidebar shows employee-specific navigation
```

## Flow 4: First Payroll Run

```
1. Admin navigates to /payroll
   → Sees employee(s) in roster

2. Admin clicks "Create Payroll Run"
   → Selects month (e.g., March 2026)
   → System pulls: employee salary, leave deductions, OT hours, claims

3. Payroll calculation runs
   → Gross salary
   → CPF (employee + employer, age-band based)
   → SDL (0.25% of gross, min $2, max $11.25)
   → SHG fund (race-based: CDAC/MBMF/SINDA/ECF)
   → FWL (if applicable: WP $300 / S Pass $450)
   → Net salary

4. Admin reviews → approves payroll run
   → Status: draft → approved

5. Admin generates payslips
   → Itemised payslips per EA s88A
   → Available at /my-payslips for employees

6. Employee checks /my-payslips
   → Sees payslip with full breakdown
   → Gross, CPF deductions, net pay, employer CPF contribution
```

## Flow 5: Employee Self-Service

```
Employee logs in → /my-dashboard

My Dashboard:
├── Employment summary (name, department, role, start date)
├── Leave balance cards (annual, sick, remaining days)
├── Quick actions (apply leave, submit claim, check attendance)
└── Recent activity

My Leave (/my-leave):
├── Balance overview per leave type
├── "Apply Leave" button
├── Leave history (pending, approved, rejected)
└── Leave type details (entitlement, taken, remaining)

My Payslips (/my-payslips):
├── List of payslips by month
├── Expandable detail view per payslip
├── Gross → deductions → net breakdown
└── Download/print option
```

## Error Flows

### Invite Link - Invalid Token

```
Employee clicks expired/invalid link
→ /signup?token=INVALID
→ Page shows: error banner
→ "This invitation link is no longer valid."
→ Options: "Contact your employer" or "Sign up as a new user"
```

### Invite Link - Already Used

```
Employee clicks link again after registering
→ /signup?token=ALREADY_USED
→ Page shows: "This invitation has already been accepted."
→ "Log in to access your account" → link to /login
```

### Company Creation - Seeding Failure

```
data.gov.sg API unavailable during public holiday fetch
→ Fallback: hardcoded 2026 Singapore public holidays
→ Admin notified: "Holiday calendar loaded from cache. Will auto-update."
→ No user-facing error
```
