# Milestone 3: Full Advisory Platform

**What users can do after this milestone**: Full advisory experience — ask any HR question, run all calculators (CPF, quota/levy, leave, notice period, overtime, retrenchment, cost-to-company), generate documents from templates, run a compliance health check, see their dashboard with alerts and action items. Emergency/urgent flow works. Consultants can switch between clients. Admin team can manage KB updates.

**Tasks**: 17

---

## T029: Dashboard — returning user (React web)

Build the returning user dashboard:

- Alert banner (if urgent regulatory changes)
- Metric cards: compliance score, pending action items, next deadline
- Recent conversations list (3-5 items with topic, date, resume button)
- Quick actions: Ask a question (primary CTA), Run a calculation, Generate a document, Run compliance check
- Pending action items from last compliance scan (checklist with risk badges)

**Red team fix S3**: This is the returning user flow — not just onboarding.

---

## T030: Dashboard — returning user (Flutter mobile)

Build matching dashboard for Flutter:

- Optimized for quick glances
- New regulatory alerts badge count
- Quick actions prominent
- Recent conversations and documents
- Pull-to-refresh

---

## T031: Calculator hub and all calculators (React + Flutter)

Build calculator hub screen with calculator cards, plus Core SDK workflows for additional calculators.

**Additional calculator workflows** (Core SDK, deterministic, no LLM):

- **Notice Period Calculator**: Input: years_of_service, contractual_notice_period, who_is_terminating. Output: applicable notice period, source (statutory vs contractual), salary-in-lieu amount.
- **Overtime Calculator**: Input: employment_type, monthly_salary, is_workman, hours_worked, day_type (normal/rest day/PH). Output: OT rate, OT pay, applicable Part IV rules. Handles monthly-rated vs hourly-rated.
- **Retrenchment Benefit Calculator**: Input: years_of_service, monthly_salary, sector. Output: statutory minimum (if applicable), market norm by sector.
- **Cost-to-Company Calculator**: Input: monthly_salary, citizenship, age, pass_type, sector. Output: total employment cost (salary + CPF employer + levy + insurance estimate).

Build calculator UI screens for all 7 calculators on both React and Flutter:

- CPF Calculator (T020 workflow)
- Foreign Worker Quota/Levy Calculator (T021 workflow) with what-if scenarios
- Leave Entitlement Calculator (T022 workflow)
- Notice Period Calculator
- Overtime Calculator
- Retrenchment Benefit Calculator
- Cost-to-Company Calculator

Pre-fill from company profile where applicable.
Results include source citations and "Ask a question about this" link.
Export calculator results as PDF.

**Red team fix R2-GAP8/9/10**: Missing calculators (overtime, retrenchment, cost-to-company) added.

---

## T032: Document template library (React web)

Build the template browsing interface:

- Grid/list toggle view
- Filter bar: All, Contracts, Policies, Letters, Forms, Checklists
- Search by template name
- Each template card: name, category tag, Generate and Preview buttons
- Full template inventory from T028 plus additional templates as KB expands

---

## T033: Document template library (Flutter mobile)

Build matching template library for Flutter:

- Vertical list of template cards
- Category filter as horizontal chip scroll
- Downloaded templates available offline (Hive/Isar local storage)

---

## T034: Document generation engine and flow

Build the document generation backend AND multi-step UI flow:

**Backend** (Core SDK workflow):

- Template engine (Jinja2 or docxtpl) for DOCX generation
- PDF generation from DOCX
- File storage (local filesystem in dev, cloud storage in production)
- Download URL generation with expiry
- Nexus endpoint: document/generate, document/preview, document/download

**Frontend flow** (React + Flutter):

- Step indicator showing progress
- Context gathering: 2-3 form fields per step, pre-filled from company profile
- Employment contract example: employment type → salary → citizenship/pass type → job title → probation period → allowances
- Document preview with highlighted sections: blue (required by EA), green (best practice), yellow (customized input)
- Download options: PDF, DOCX
- Save to account for future reference
- "Need changes? Ask the advisor" link

Uses DocumentGenerationAgent → Core SDK document workflow.

**Red team fix R2-G06**: Document generation backend is a dedicated engineering task, not just a UI.

---

## T035: Compliance health check (React + Flutter)

Build the compliance scanning feature:

- Profile verification step (confirm company details current)
- Scan runs using ComplianceAgent coordinating with all domain specialists
- Results displayed prioritized by risk:
  - RED (High Priority): statutory violations, immediate penalties
  - AMBER (Medium Priority): guideline compliance gaps
  - GREEN (Good Practice): recommended improvements
- Each finding: risk badge, title, one-line explanation, consequence, "Fix this" CTA (links to template or advisory)
- Compliance score gauge (X/100)
- Action plan: prioritized checklist, progress tracking
- Save results, compare to previous check
- Export compliance report as PDF
- **Inspection readiness mode**: "Am I ready for an MOM inspection?" checklist based on company profile
- **Document upload for review**: upload existing contracts/policies for AI compliance review against current regulations

**Red team fix R2-GAP13**: Inspection readiness is a mode within compliance check.
**Red team fix R2-GAP12**: Document upload for compliance review addresses Persona C and D needs.

---

## T036: Emergency/urgent flow (React + Flutter)

Build the emergency response flow:

- Accessible from dashboard quick action: "I have an urgent HR situation"
- Also triggered when advisory classifies a query as RED risk
- Emergency topic cards: TADM claim, workplace injury, wrongful dismissal, MOM inspection, discrimination complaint, data breach, other
- Structured emergency response:
  - Section 1: "Your immediate obligations" (numbered, with deadlines)
  - Section 2: "Documents you need to gather" (checklist)
  - Section 3: "Step-by-step process" (timeline stepper)
  - Section 4: "When to get professional help" (prominent, not fine print)
- "Connect to employment law specialist" CTA
- Downloadable response as PDF
- Red visual styling (red left border, warning icon header)

**Red team fix C2**: This addresses the missing emergency user flow.

---

## T037: Multi-client support — consultant view (React + Flutter)

Build consultant-specific features:

- Client list page: table/grid of clients with company name, sector, employee count, compliance score, last activity
- Client switcher: persistent dropdown in top bar (web) / swipe-accessible panel (mobile)
- Switching client updates: dashboard data, calculator pre-fills, compliance status, conversation context
- Visual confirmation toast: "Now viewing: ABC Pte Ltd"
- Add new client flow (creates new Company in DataFlow with multi-tenant link)
- Per-client advisory history and compliance tracking
- Bulk export: per-client compliance reports and advisory summaries

**Red team fix C4**: Multi-client support is in this milestone, not deferred.

---

## T038: Regulatory alerts system (React + Flutter)

Build the regulatory change alert system:

- Alert list page: chronological, most recent first
- Filter: All / Affecting your company / Upcoming changes
- Each alert: date, impact badge, title, one-line summary
- Alert detail page: what changed (plain language), how it affects your company (calculated from profile), what you need to do (numbered actions), timeline, comparison table, source/effective date
- **Regulatory calendar view**: upcoming changes with effective dates in calendar format
- CTAs: Update calculator, Ask a question, Generate updated policy
- Push notifications (Flutter via FCM)
- **Email notification infrastructure**: email service provider integration (SendGrid or AWS SES), transactional email templates, unsubscribe management
- In-app notification bell with badge count

**Red team fix R2-GAP14**: Regulatory calendar view added.
**Red team fix R2-G07**: Email notification infrastructure included.

---

## T039: Company profile and user settings (React + Flutter)

Build company profile view/edit AND unified user settings:

**Company profile**:

- Card-based layout showing all profile sections
- Edit mode per section (not a giant form)
- Profile completeness indicator with list of missing items
- Warning when profile changes affect compliance: "Updating employee count may change requirements. Run a new health check?"
- History of profile changes (for audit)
- Profile change event hooks: detect when headcount crosses regulatory thresholds (feeds T048 growth triggers)

**User settings**:

- Text size preference: Normal / Large / Extra Large (persisted per user)
- Notification preferences: which alert types, frequency, channels (push/email/in-app)
- Language preference (English only at launch, infrastructure ready)
- Data export: export all your data (conversations, compliance reports, documents) — PDPA compliance
- Account deletion flow — PDPA right to erasure

**Red team fix R2-GAP3**: Unified settings screen for all user preferences.
**Red team fix R2-GAP7**: Data export for PDPA compliance and consultant needs.

---

## T040: Regulatory change management pipeline

Build the operational infrastructure for keeping the KB current:

**Phase 1 — Manual update workflow** (launch requirement):

- Admin creates regulatory update: affected provisions, new text, effective date, urgency
- Staging area: proposed changes visible for review before publication
- Human-in-the-loop validation: domain expert reviews and approves/rejects staged updates
- Publication workflow: approved updates go live — update KB provisions, generate user alerts (T038), update rate tables
- Staleness tracking: every provision has next_review_date, automated alerts when approaching

**Phase 2 — Automated monitoring** (post-launch enhancement):

- Source monitoring: automated checks of MOM, CPF Board, IRAS, TAFEP websites for changes
- Change detection alerts for human review
- URL structure change detection with fallback alerts

**Red team fix M4**: This is the operational process for the 48-hour update SLA.
**Red team fix S1**: Source monitoring includes URL structure change detection with fallback alerts.
**Red team fix R2-R04**: Split into manual (launch) and automated (post-launch) phases.

---

## T041: Admin and operations interface

Build the internal admin interface for platform operations:

- KB management dashboard: provision counts by domain, staleness status, last update dates
- Regulatory update staging and review workflow UI (supports T040)
- Error correction review interface (supports T044)
- User feedback review dashboard: browse thumbs down responses, categorize issues, track resolution
- Expert audit interface: random sample of advisory responses for review, with full trust lineage and reasoning chain visibility
- Basic platform metrics: active users, queries per day, response confidence distribution, risk-tier distribution

This is an internal tool, not user-facing. Can be a simple React admin panel.

**Red team fix R2-I03**: Admin interface is required for KB updates, error corrections, and accuracy monitoring to function.
**Red team fix R2-REC5**: Expert-facing reasoning transparency ensures human governors understand the system.

---

## T042: Abuse prevention and guardrails

Build safety systems for the advisory platform:

- Query screening: detect requests to help circumvent employment law (underpaying below PWM, avoiding CPF, illegal deductions)
- Response: refuse to assist with non-compliance, explain why the practice is problematic and what the legal consequences are
- Adversarial prompt injection protection
- Rate limiting per user/session
- Logging of flagged queries for review
- Content filtering: ensure no agents generate discriminatory or TAFEP-violating advice
- **Mandatory escalation criteria**: queries involving active litigation, criminal liability, or below-threshold confidence must not receive AI answers — route to human specialist only

**Red team fix S5**: Platform abuse scenarios addressed.
**Red team fix R2-REC4**: Mandatory escalation for cases where AI advice is insufficient.

---

## T043: Singlish and natural language robustness

Ensure the platform handles real Singapore English input:

- Test with Singlish HR queries: "My staff resign already, need pay notice period or not?", "Can forfeit MC if never take?", "How to calculate OT for part-timer?"
- Ensure LLM system prompts handle code-switching (English + Mandarin/Malay keywords)
- Disable autocorrect on all chat inputs (both React and Flutter)
- Suggested question examples in natural Singlish where appropriate
- Voice input configured for Singapore English accent model

**Red team fix M2**: Singlish handling is a launch requirement, not Phase 5.
