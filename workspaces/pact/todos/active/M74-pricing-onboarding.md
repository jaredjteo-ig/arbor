# M74: Pricing, Onboarding, and Data Governance

**Milestone**: M74 (freemium tiers, feature gating, data export, retention policy)
**Priority**: HIGH — without a working free tier the product cannot acquire users
**Scope**: both
**Estimated effort**: 4-5 days

Per gap resolution H2, the freemium model is:

- Free: advisory (unlimited), calculators, compliance dashboard, employee directory. No agents.
- Starter ($49/month): 1 agent (Arbor HR or Arbor Payroll). Up to 10 employees.
- Growth ($149/month): All 3 agents. Up to 50 employees.
- Custom: larger companies, consultant access, API.

Per gap M6: data export must be available on all tiers (PDPA right to erasure,
portability). Per gap M8: data retention policy and deletion must be documented
and implemented.

Value critique finding: the landing page currently says "It's Free" without
defining what is free. This must be fixed.

---

### T474: Subscription tier model and feature flags

**Scope**: backend
**Depends**: T402
**Files**:

- `src/hr_advisory/models/company_user.py` (extend Company model)
- `src/hr_advisory/pact/tier_gates.py` (new)

**Description**: Add subscription tier to Company model and implement
feature gating throughout the platform.

Add to Company model:

- `subscription_tier: str default "free"` — values: `free`, `starter`, `growth`, `custom`
- `tier_updated_at: DateTime nullable`
- `tier_employee_limit: Integer nullable` — NULL = use tier default
- `agent_slot_limit: Integer nullable` — NULL = use tier default

`tier_gates.py`:

```python
TIER_DEFINITIONS = {
    "free": {
        "max_employees": 10,
        "max_agents": 0,
        "advisory": True,
        "calculators": True,
        "compliance_dashboard": True,
        "employee_directory": True,
        "morning_briefing": True,
        "held_actions": False,
        "agent_activation": False,
        "pact_features": False,
        "data_export": True,
        "whatsapp_notifications": False,
    },
    "starter": {
        "max_employees": 10,
        "max_agents": 1,
        "advisory": True,
        "calculators": True,
        "compliance_dashboard": True,
        "employee_directory": True,
        "morning_briefing": True,
        "held_actions": True,
        "agent_activation": True,
        "pact_features": True,
        "data_export": True,
        "whatsapp_notifications": False,
    },
    "growth": {
        "max_employees": 50,
        "max_agents": 3,
        "advisory": True,
        "calculators": True,
        "compliance_dashboard": True,
        "employee_directory": True,
        "morning_briefing": True,
        "held_actions": True,
        "agent_activation": True,
        "pact_features": True,
        "data_export": True,
        "whatsapp_notifications": True,
    },
    "custom": {
        "max_employees": None,  # unlimited
        "max_agents": None,     # unlimited
        # all features True
    },
}

def check_tier(company: Company, feature: str) -> bool:
    """Returns True if company's tier includes the feature."""

def require_tier(company: Company, feature: str) -> None:
    """Raises TierUpgradeRequired if feature not available."""

class TierUpgradeRequired(Exception):
    def __init__(self, feature: str, required_tier: str): ...
```

**Acceptance criteria**:

- [ ] Company model has `subscription_tier` field, default "free"
- [ ] `check_tier("free", "agent_activation")` returns False
- [ ] `check_tier("starter", "agent_activation")` returns True
- [ ] `require_tier` raises `TierUpgradeRequired` with correct tier info
- [ ] Free tier allows advisory (must not break existing advisory users)
- [ ] Unit tests: all tier/feature combinations

---

### T475: Feature gating enforcement in API endpoints

**Scope**: backend
**Depends**: T474
**Files**:

- `src/hr_advisory/api/routers/pact.py` (modify)
- `src/hr_advisory/api/routers/shadow.py` (modify — advisory)
- `src/hr_advisory/api/routers/advisory.py` (modify)

**Description**: Enforce tier gates at the API layer. Return 402 Payment
Required with upgrade information when a feature is gated.

Standard 402 response format:

```json
{
  "detail": "This feature requires the Starter plan.",
  "upgrade_to": "starter",
  "feature": "agent_activation",
  "upgrade_url": "/settings/billing"
}
```

Gates to enforce:

- `POST /api/pact/agents/{id}/activate` → requires `agent_activation`
- `POST /api/pact/held-actions/{id}/resolve` → requires `held_actions`
- `POST /api/pact/bridges/{id}/activate` → requires `pact_features`
- `PATCH /api/pact/notification-settings` (WhatsApp) → requires `whatsapp_notifications`
- Employee import beyond 10 → requires tier with higher `max_employees`
- Advisory: no gate (free tier) — verify NOT gated

**Advisory MUST remain free** — this is explicit in the pricing model.
Do NOT gate any `POST /api/advisory/` endpoints.

**Acceptance criteria**:

- [ ] Agent activation returns 402 on free tier
- [ ] Advisory endpoints return 200 on free tier (not gated)
- [ ] 402 response includes `upgrade_to` and `upgrade_url`
- [ ] Starter tier can activate 1 agent but not 2nd agent (max_agents=1)
- [ ] Growth tier can activate all 3 agents
- [ ] Integration test: free company tries to activate agent → 402

---

### T476: Tier upgrade API and billing settings page

**Scope**: both
**Depends**: T474
**Files**:

- `src/hr_advisory/api/routers/billing.py` (new)
- `apps/web/app/(dashboard)/settings/billing/page.tsx` (new)
- `apps/web/components/settings/PricingCards.tsx` (new)
- `apps/web/components/settings/UpgradeBanner.tsx` (new)

**Description**: In-app billing management. For MVP, this is a "contact us"
flow — no Stripe integration yet. Stripe can be added in a follow-on milestone.
The tier is updated manually by support after payment confirmation.

Backend:

`POST /api/billing/upgrade-request`:

- Body: `{requested_tier: str, contact_email: str, notes: str nullable}`
- Creates an `UpgradeRequest` DataFlow model: `company_id`, `requested_tier`,
  `contact_email`, `notes`, `status: pending`, `created_at`
- Sends email to `billing@arbor.terrene.dev` with request details
- Returns `{request_id, status: "pending", message: "We'll be in touch within 24 hours."}`

`GET /api/billing/current`:

- Returns `{tier, max_employees, max_agents, features: dict}`
- All users in company can read

`POST /api/billing/tier` (internal/admin only):

- Sets `company.subscription_tier` directly — for support use
- Requires `is_superuser=True` on the calling user
- Creates audit event

`UpgradeBanner` component:

- Shown on dashboard when user hits a tier gate (402 response received)
- "Upgrade to {tier} to unlock {feature}"
- "Learn more" → `/settings/billing`

`PricingCards`:

- 3 cards: Free / Starter / Growth
- Current tier highlighted
- Feature comparison checklist per card
- "Upgrade" button → opens upgrade request form

**Acceptance criteria**:

- [ ] Upgrade request creates UpgradeRequest record and sends email
- [ ] `GET /api/billing/current` returns accurate tier info
- [ ] Admin `POST /api/billing/tier` changes tier (superuser only)
- [ ] UpgradeBanner appears on dashboard after 402 response
- [ ] PricingCards shows 3 tiers with correct feature lists
- [ ] Current tier is highlighted on pricing cards

---

### T477: Employee count enforcement

**Scope**: backend
**Depends**: T474, T438
**Files**:

- `src/hr_advisory/api/routers/employees.py` (modify)
- `src/hr_advisory/services/employee_import.py` (modify)

**Description**: Enforce tier employee limits at creation and import.

Add to `POST /api/employees`:

- Count active employees for the company
- If count >= tier `max_employees`: return 402 with upgrade info
- Exception: if `max_employees = None` (custom tier), no limit

Add to `POST /api/employees/import`:

- Pre-flight: count existing + rows to import
- If total would exceed `max_employees`: return 402
  - Body: `{detail: "Importing {N} employees would exceed your plan limit of {M}.",
upgrade_to: ..., current_count: ..., limit: ..., rows_requested: ...}`

**Acceptance criteria**:

- [ ] Free tier: 11th employee creation returns 402
- [ ] Starter tier: 11th employee creation returns 402 (same limit)
- [ ] Growth tier: 51st employee returns 402
- [ ] Import check runs before any rows are processed
- [ ] Import that would reach limit by 5 returns 402 with clear count
- [ ] Integration test: import 12 employees on free tier → 402 at row 11

---

### T478: Data export (PDPA portability)

**Scope**: backend
**Depends**: T474
**Files**:

- `src/hr_advisory/api/routers/data_export.py` (new)
- `src/hr_advisory/services/data_exporter.py` (new)

**Description**: Per gap M6 and PDPA data portability requirements, companies
must be able to export all their data. Available on all tiers (Free included).

`POST /api/data-export/request`:

- Body: `{format: "json" | "csv", scope: "full" | "employees" | "payroll" | "leave"}`
- Creates `DataExportRequest` model: `company_id`, `format`, `scope`,
  `status: queued`, `requested_by`, `created_at`
- Queues async export job
- Returns `{export_id, status: "queued", estimated_minutes: 5}`

`GET /api/data-export/{export_id}`:

- Returns export status: `{status, download_url nullable, expires_at nullable}`
- `status` values: `queued`, `processing`, `ready`, `expired`, `failed`
- Download URL is pre-signed (valid 24 hours from generation)

`data_exporter.py`:

`generate_export(company_id: int, format: str, scope: str) -> bytes`:

- Employees: name, email, job_title, start_date, employment_type (NO salary, NO bank)
  — salary data excluded from default export per PDPA minimization
- Payroll: anonymized — `{employee_id, month, gross_pay, cpf_ee, cpf_er, net_pay}`
  — no employee names in payroll export (link by ID)
- Leave: `{employee_id, start_date, end_date, type, status, approved_by}`
- Full: all of the above as separate sections in JSON, or separate CSV files in ZIP

`DataExportRequest` DataFlow model:

- `company_id`, `format`, `scope`, `status`, `requested_by`, `download_url nullable`,
  `expires_at nullable`, `created_at`

**Acceptance criteria**:

- [ ] Export request creates DataExportRequest with status=queued
- [ ] JSON export contains all requested scope data
- [ ] CSV export is valid UTF-8 with BOM (for Excel compatibility)
- [ ] Salary data excluded from employee exports (PDPA minimization)
- [ ] Download URL expires after 24 hours
- [ ] Employee who didn't request the export cannot download it
- [ ] Integration test: request export, wait for ready status, download, verify content

---

### T479: Data retention policy and deletion

**Scope**: backend
**Depends**: T478
**Files**:

- `src/hr_advisory/services/data_retention.py` (new)
- `src/hr_advisory/api/routers/data_export.py` (extend)

**Description**: Per gap M8, implement documented data retention policy with
automated cleanup. Per PDPA, companies have the right to erasure.

Data retention rules:

- Active company data: retained indefinitely
- Terminated employee PII (NRIC, bank details): anonymized after 2 years
- Payroll records: retained 5 years (IRAS requirement)
- Leave records: retained 2 years (EA requirement)
- Audit logs (PdpaAccessLog, PactAuditEvent): retained 7 years
- Inactive company data (no login in 12 months): anonymized after 18 months notice

`data_retention.py`:

`anonymize_terminated_employee_pii(employee_id: int) -> bool`:

- Sets `Employee.nric = "[REDACTED]"`, `Employee.bank_account_number = "[REDACTED]"`
- Sets `Employee.phone = None`, `Employee.personal_email = None`
- Appends to `Employee.timeline`: `{event: "pii_anonymized", date: today}`
- Returns True on success

`schedule_retention_cleanup(company_id: int) -> dict`:

- Finds terminated employees where `termination_date < 2 years ago`
  AND `pii_not_yet_anonymized`
- Returns `{employees_to_anonymize: N}` (preview, does not execute)

`POST /api/data-export/delete-account`:

- Deletes all company data immediately
- Sends confirmation email
- Owner only
- Cascades: employees, payroll, leave, claims, audit logs
- Exception: retains minimal legal record — `{company_id, registered_uen, deletion_date}`
  (cannot be deleted — legal retention requirement)
- Creates a `CompanyDeletionRecord` (append-only, immutable)

**Acceptance criteria**:

- [ ] `anonymize_terminated_employee_pii` redacts NRIC and bank fields
- [ ] Timeline entry created on anonymization
- [ ] `schedule_retention_cleanup` returns correct count without executing
- [ ] Delete account endpoint requires owner authentication
- [ ] Post-deletion: company cannot log in, data not retrievable
- [ ] Legal minimum record retained after deletion
- [ ] Unit test: anonymize employee, verify fields redacted, verify timeline entry

---

### T480: Landing page — free tier definition

**Scope**: frontend
**Depends**: T474
**Files**:

- `apps/web/app/(marketing)/page.tsx` (modify)
- `apps/web/app/(marketing)/pricing/page.tsx` (new)

**Description**: Per the value critique finding: the landing page currently
says "It's Free" without defining what is free. This creates false expectations.
Fix the messaging.

Landing page changes:

- Replace "It's Free" CTA with "Start free — no credit card required"
- Add subtext: "Advisory and calculators always free. Activate agents from
  $49/month."
- Add "How pricing works" section with 3-column card layout
- Link to `/pricing` for full comparison

`/pricing` page:

- Three-column pricing table: Free / Starter ($49) / Growth ($149)
- Feature rows: Advisory, Employee management, Morning briefings, Agents,
  Employee limit, WhatsApp notifications
- FAQ section:
  - "Is advisory really free?" — Yes, unlimited. No time limit.
  - "Can I try agents before paying?" — The first 14 days after activation are
    free (trial). After that, $49/month.
  - "Can I export my data?" — Yes, always, on all tiers.
- "Start free" CTA → `/register`
- "Talk to us" for Custom tier → `billing@arbor.terrene.dev`

**Acceptance criteria**:

- [ ] Landing page no longer says "It's Free" without qualification
- [ ] Pricing page shows all 3 tiers with accurate feature lists
- [ ] Feature lists match `TIER_DEFINITIONS` from T474 (not hardcoded)
- [ ] FAQ answers the 3 questions listed above
- [ ] "Start free" links to registration
- [ ] Mobile-friendly layout for pricing table (cards stack on mobile)
