# Architecture Decisions: Onboarding Completion

## ADR-1: Invite Token Delivery

### Context

The backend creates invitation tokens but doesn't return them in the response (security measure). There's no email delivery system. Admins cannot get the token to employees.

### Options

1. **Return token in API response** — Admin copies link manually (email, WhatsApp, etc.)
2. **Build email delivery** — Integrate SendGrid/SES to email invite links automatically
3. **Both** — Return token AND send email

### Decision: Option 1 (Return token in response)

- MVP-appropriate: works immediately, no external service dependency
- Admin can share via any channel (WhatsApp is dominant in SG SMEs)
- Security: token is single-use, 7-day expiry, email-locked
- Future: add email delivery as enhancement

### Implementation

- Modify POST /employees/invite to return `{ message, invite_url }`
- Frontend constructs clickable link for admin to copy/share
- invite_url format: `{FRONTEND_URL}/signup?token={token}`

## ADR-2: Default Data Seeding Strategy

### Context

Companies need operational data (leave types, claim categories) to use HRIS modules. Currently none are seeded automatically.

### Options

1. **Seed on company creation** — All defaults created in the company creation handler
2. **Seed on first module access** — Lazy seeding when user first visits payroll/leave/claims
3. **Manual setup wizard** — Walk admin through configuring each module

### Decision: Option 1 (Seed on company creation)

- Eliminates "empty state" problem across all modules
- Ensures payroll can run immediately after first employee is added
- Leave seed function already exists (`_seed_statutory_leave_types`)
- Claim categories are simple creates
- Public holidays fetched from data.gov.sg API with hardcoded fallback

### What to Seed

1. **Leave types** — Call existing `_seed_statutory_leave_types(company_id)`
2. **Claim categories** — 4 defaults: Transport, Meals, Medical, Office Supplies
3. **Attendance settings** — Persist the existing hardcoded defaults to DB
4. **Public holidays** — Fetch from data.gov.sg for current year, store in DB

## ADR-3: Invite Acceptance Page Route

### Context

Need a frontend page where employees land after clicking an invite link.

### Options

1. **`/signup?token={token}`** — Extend existing signup page
2. **`/invite/{token}`** — Dedicated invite acceptance page
3. **`/join?token={token}`** — Separate join page

### Decision: Option 1 (`/signup?token={token}`)

- Reuses existing auth layout (ValuePropositionPanel)
- Single registration surface (less confusion)
- Token presence switches behavior: standard signup vs invite acceptance
- Invite flow shows company name and role being offered

### UX Flow

1. Employee clicks invite link → `/signup?token=abc123`
2. Page detects token, calls GET /employees/invite/{token} to validate
3. Shows: "You've been invited to join [Company Name] as [Role]"
4. Pre-fills email (from invitation), asks for name + password
5. On submit: POST /auth/register-employee
6. On success: auto-login, redirect to /my-dashboard

### Error States

- Invalid token → "This invitation is invalid or has expired. Contact your employer."
- Already accepted → "This invitation has already been used."
- Token loading → skeleton/spinner

## ADR-4: Public Landing Page

### Context

No public-facing page exists. All visitors see the login page.

### Options

1. **ManagementShowcase as root page** — Use existing component at `/`
2. **Keep login as entry** — No change
3. **New marketing page** — Build dedicated landing page

### Decision: Option 1 (ManagementShowcase at root)

- Component already built and comprehensive
- Shows all 8 modules with feature details
- Has hero, value props, and CTAs
- Login/signup links added to header
- Root `/` becomes public, `/login` and `/signup` remain separate

### Implementation

- Create `app/page.tsx` (public, no auth required)
- Import ManagementShowcase, add navigation header with Login/Sign Up
- Ensure root layout doesn't wrap in ProtectedRoute
