# Arbor HR Operations Engine Deck — Reality Check Against Codebase

**Source**: `Arbor-HR-Operations-Engine_Annex_ConfidentialCAPL.pdf` (13 slides)
**Date**: 2026-03-26
**Purpose**: Map every claim in the deck to what's actually built, what's planned, and what's a gap

---

## Key Context from the Deck

This deck was not written for a general audience — it's written for **Ricoh Thailand** specifically and references:

- **Project Meridian** — Ricoh Thailand's AI transformation initiative (moving 2,000 staff through AI transformation)
- **AI Academy** — a companion training/upskilling product (not part of Arbor)
- **JourneyMate** — another companion product (likely AI career development, not part of Arbor)
- **AURORA** — appears on slide 12 as a brand/logo — may be the umbrella brand for the Meridian suite

The deck positions Arbor as **"the HR and compliance backbone of Project Meridian"** — not a standalone HR tool, but the operational foundation that keeps people data, payroll, leave, and legal obligations running smoothly while Ricoh transforms.

This is a much stronger positioning than "here's an HR platform." It makes Arbor essential infrastructure for the transformation, not an optional tool.

---

## Eight Pillars — Mapped to Codebase Reality

### Pillar 1: Employee Records & Workflows

**Deck claims**:

- Complete profiles (roles, salary, promotions, transfers, documents, skills)
- Joining & leaving (onboarding with contracts, offboarding with final pay)
- Staff self-service (view profiles, payslips, balances)

**Reality**:

| Claim                 | Status      | Evidence                                                                                                                                   |
| --------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| Complete profiles     | **Live**    | `employees.py` — ~50 endpoints, full CRUD with salary components, emergency contacts, employment history, documents, skills, custom fields |
| Joining (onboarding)  | **Live**    | Employee invitation registration, KET generation, company seeding auto-creates policies                                                    |
| Leaving (offboarding) | **Partial** | Final salary calculation exists in payroll. Formal offboarding workflow (exit checklist, asset return tracking) is **Planned** not built   |
| Staff self-service    | **Live**    | `/my-dashboard`, `/my-leave`, `/my-payslips`, `/my-timesheets`, `/my-inventory`                                                            |

**Gap**: Offboarding workflow is claimed as automatic ("tracks assets, final pay, and paperwork automatically") but formal offboarding with exit checklist is not yet built as a dedicated workflow. The components exist (payroll can do final calc, inventory tracks assets) but they're not wired into a single offboarding flow.

**Risk for demo**: Low — the individual features work. The gap is the automated sequencing, not the capabilities.

---

### Pillar 2: Payroll & Leave for Thailand

**Deck claims**:

- Draft → review → approve → paid workflow
- Country-aware rules (Thai social security, tax withholding, statutory leave)
- Clear payslips and reports (itemised, YTD, no manual spreadsheets)

**Reality**:

| Claim                                              | Status      | Evidence                                             |
| -------------------------------------------------- | ----------- | ---------------------------------------------------- |
| Payroll workflow (draft → review → approve → paid) | **Live**    | `payroll.py` — full workflow with status transitions |
| Payslip generation                                 | **Live**    | PDF generation, email delivery, itemised             |
| YTD reports                                        | **Live**    | CPF YTD tracking per employee                        |
| Country-aware rules — **Singapore**                | **Live**    | CPF, SDL, FWL, SHG all calculated                    |
| Country-aware rules — **Thailand SSF**             | **Planned** | `T040` in roadmap — not built yet                    |
| Country-aware rules — **Thailand PIT**             | **Planned** | `T041` in roadmap — not built yet                    |
| Thai statutory leave types                         | **Planned** | `T039` in roadmap — not built yet                    |
| Thai statutory filing (SSO, PND 1)                 | **Planned** | `T050` in roadmap — not built yet                    |

**Gap**: The deck says "Thai social security, tax withholding, and statutory leave types — not generic templates." This is the biggest promise-vs-reality gap. The payroll engine is live and production-grade for Singapore. Thailand statutory calculations (SSF, PIT, Thai leave types) are scoped and designed but **not yet implemented**.

**Risk for demo**: HIGH if they expect to see Thai payroll working. The demo strategy (show SG as proof of architecture, frame TH as PoC deliverable) handles this, but the deck explicitly promises "Country-Aware Rules" for Thailand.

---

### Pillar 3: Everyday HR Tasks

**Deck claims**:

- Leave & attendance (online requests, manager approvals, calendars, overtime, off-in-lieu)
- Claims & expenses (receipts, approval, flows into payroll)
- Shifts & projects (schedules, hours tracking, cost centre linking)

**Reality**:

| Claim                | Status   | Evidence                                                                  |
| -------------------- | -------- | ------------------------------------------------------------------------- |
| Leave management     | **Live** | `leave.py` — 18 endpoints, all features claimed                           |
| Attendance           | **Live** | `attendance.py` — 17 endpoints, clock in/out, overtime, timesheets        |
| Claims with receipts | **Live** | `claims.py` — 18 endpoints, receipt upload, approval, payroll integration |
| Shift scheduling     | **Live** | `shifts.py` — 17 endpoints, templates, assignments, publish               |
| Projects & costing   | **Live** | `projects.py` — 17 endpoints, assignments, rates, cost calc               |

**Gap**: None. Every feature claimed in Pillar 3 is live and functional.

---

### Pillar 4: Performance, Skills, and Growth

**Deck claims**:

- Structured reviews (quarterly/annual, self-assessment, manager ratings, sign-off)
- Live skills inventory (real-time capability map)
- Future: Goals, OKRs, improvement plans — tying into AI Academy and JourneyMate

**Reality**:

| Claim                   | Status        | Evidence                                                                        |
| ----------------------- | ------------- | ------------------------------------------------------------------------------- |
| Structured reviews      | **Live**      | `appraisals.py` — templates, periods, self-assessment, manager review, sign-off |
| Skills inventory        | **Live**      | Employee skills tracking in `employees.py`                                      |
| Goals/OKRs              | **Future**    | Not built — correctly labelled "Future" in the deck                             |
| AI Academy integration  | **Not Arbor** | This is a separate product in the Meridian suite                                |
| JourneyMate integration | **Not Arbor** | Separate product                                                                |

**Gap**: None for what Arbor owns. The "Future" items are honestly labelled. The AI Academy and JourneyMate references are external products that Arbor would integrate with, not features Arbor needs to build.

---

### Pillar 5: Embedded Legal Guidance

**Deck claims**:

- AI advisory that answers employment questions in plain language with links to Thai regulations
- Risk classification (HIGH / MEDIUM / LOW) so HR knows when to proceed vs when to seek professional advice

**Reality**:

| Claim                               | Status      | Evidence                                                                            |
| ----------------------------------- | ----------- | ----------------------------------------------------------------------------------- |
| AI advisory with citations          | **Live**    | Advisory engine with 6 SG regulatory domains, SSE streaming, legal citations        |
| Risk classification                 | **Live**    | 3-tier system (GREEN/AMBER/RED — the deck says HIGH/MEDIUM/LOW which is equivalent) |
| Links to Thai regulations           | **Planned** | Currently cites SG regulations. Thai KB is planned (T039-T045)                      |
| 13-step safety chain                | **Live**    | Every query, every time                                                             |
| Professional referral for high-risk | **Live**    | RED-tier includes explicit "consult a lawyer"                                       |

**Gap**: The deck says "links to underlying Thai regulations" — this is the Thailand KB which is planned but not built. The advisory engine architecture is proven with Singapore. The Thailand content is the PoC deliverable.

**Risk for demo**: Same as Pillar 2 — the architecture works, the Thai content doesn't exist yet. Demo strategy handles this by showing SG as proof.

---

### Pillar 6: HR Co-Pilot

**Deck claims**:

- Plain-language commands ("show pending leave approvals", "start payroll for this month")
- Human always in the loop (nothing finalised without HR approval)
- Proactive nudges (expiring permits, upcoming filings, overdue approvals)

**Reality**:

| Claim                                 | Status   | Evidence                                                  |
| ------------------------------------- | -------- | --------------------------------------------------------- |
| Plain-language commands               | **Live** | Shadow agent intent classification + workflow composition |
| PACE safety model (human in the loop) | **Live** | Preview → Approve → Confirm → Exit                        |
| Proactive nudges                      | **Live** | `nudges.py` — page-aware, deterministic                   |
| Proactive briefing                    | **Live** | `briefing.py` — morning briefing cards                    |
| Entity resolution ("John" → employee) | **Live** | `entity_resolver.py`                                      |

**Gap**: None. The shadow agent is fully built. Every feature claimed in Pillar 6 is live.

---

### Pillar 7: Compliance, Privacy, and Trust

**Deck claims**:

- PDPA-ready behaviour (access logging, encryption, role-based controls)
- Security as default (sign-in, brute-force protection, company data isolation)
- Audit-friendly reporting (compliance views, downloadable reports)

**Reality**:

| Claim                | Status   | Evidence                                                |
| -------------------- | -------- | ------------------------------------------------------- |
| PDPA access logging  | **Live** | `PdpaAccessLog` model, access audit trail               |
| Field encryption     | **Live** | NRIC, bank accounts encrypted with Fernet               |
| Role-based controls  | **Live** | OWNER, HR_MANAGER, CONSULTANT, EMPLOYEE, platform_admin |
| Tenant isolation     | **Live** | company_id enforced on every query                      |
| Rate limiting        | **Live** | Per-IP auth, per-user advisory                          |
| Compliance dashboard | **Live** | `/compliance` with category scoring                     |
| EATP trust lineage   | **Live** | Cryptographic audit trail on every advisory response    |

**Gap**: None. Security and compliance features are among the most thoroughly built and tested parts of the platform (7 red team rounds, 22+ security issues found and fixed).

---

### Pillar 8: Built to Scale Regionally

**Deck claims**:

- Multi-country roadmap (Singapore live, Thailand planned, Malaysia/Vietnam/Indonesia/Philippines follow)
- Integration-ready (accounting, communications, government portals)
- Mobile access (leave, claims, HR information on mobile)

**Reality**:

| Claim                    | Status      | Evidence                                                        |
| ------------------------ | ----------- | --------------------------------------------------------------- |
| Singapore live           | **Live**    | 6 domains, 7 calculators, 89+ provisions                        |
| Thailand planned         | **Planned** | Roadmap T039-T052, scoped in detail                             |
| ASEAN expansion          | **Future**  | Architecture supports it, no content yet                        |
| Integration architecture | **Live**    | 35+ MCP adapters with circuit breakers, retry, PII filtering    |
| Integration connections  | **Planned** | Adapters coded but require partner API credentials              |
| Mobile app               | **Live**    | Full Flutter app — advisory, calculators, compliance, documents |

**Gap**: The integrations are architecturally ready but not connected to live external services (need Xero API key, government CorpPass credentials, etc.). The deck correctly says "Planned connectors" which is accurate.

The "Meridian objective" callout on this slide is the reseller angle: "Gives Ricoh Thailand an HR engine that can later be offered as part of the Meridian suite to regional clients — not just used internally." This is a revenue play, not just a cost play.

---

## "How Arbor Serves Project Meridian" — The 5-Step Value Chain

The deck maps Arbor to Meridian's transformation goals:

| Step                 | Meridian Need                                       | Arbor Feature                                          | Status                                     |
| -------------------- | --------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------ |
| 1. Admin Freed       | Free HR from routine admin for AI adoption          | Self-service, automation, approval workflows           | **Live**                                   |
| 2. Payroll Trust     | Accurate pay prevents staff confidence erosion      | Deterministic payroll engine with statutory deductions | **Live** (SG), **Planned** (TH)            |
| 3. Talent Visibility | Skills map for roles shifting from print to digital | Skills inventory, employee profiles, appraisals        | **Live**                                   |
| 4. Legal Confidence  | Embedded Thai law reduces exposure                  | Advisory engine with citations and risk tiers          | **Live** (SG), **Planned** (TH)            |
| 5. Regional Scale    | From internal tool to Meridian suite offering       | Multi-jurisdiction architecture, mobile, integrations  | **Architecture Live**, **Content Planned** |

This value chain is strong because it ties every Arbor feature to a specific Meridian transformation objective. It's not "here's an HR tool" — it's "here's the infrastructure that prevents HR from becoming a bottleneck during your AI transformation."

---

## Critical Observations

### 1. The Deck Uses "Arbor" — We Rebranded to "Central"

The entire deck says "Arbor" and uses Arbor branding. Our codebase and deployment config now say "Central" at `central.kailash.ai`.

**Decision needed**: Either:

- (a) Keep the deck as "Arbor" and revert the UI rebrand back to "Arbor" (the deck was already shared or is ready to share)
- (b) Update the deck to say "Central" to match the deployment

If this deck has already been shared with Ricoh Thailand, keep "Arbor" everywhere. Don't create confusion by changing names mid-engagement.

### 2. The Deck Already Promises Thai-Specific Features

Pillar 2 explicitly says "Thai social security, tax withholding, and statutory leave types." Pillar 5 says "links to underlying Thai regulations." These are promised, not delivered. The demo strategy (show SG, frame TH as PoC) still works, but the audience has already seen these promises in writing.

### 3. Project Meridian Context Is New and Important

The deck references "Project Meridian" as Ricoh Thailand's AI transformation programme. This changes the pitch:

- **Without Meridian context**: "Here's an HR platform with AI advisory"
- **With Meridian context**: "Here's the HR backbone that ensures 2,000 people are managed correctly while you transform"

The Meridian framing makes Arbor a necessity, not an option. The 5-step value chain (Admin Freed → Payroll Trust → Talent Visibility → Legal Confidence → Regional Scale) is a much stronger narrative than any feature list.

### 4. "AURORA" Brand Appears on Slide 12

The closing slide shows an "AURORA" logo. This may be the umbrella brand for the Meridian suite (Arbor + AI Academy + JourneyMate = Aurora?). Clarify this before the meeting — the audience may know this brand.

### 5. The Deck Already Has the Reseller Angle

Pillar 8's Meridian objective: "Gives Ricoh Thailand an HR engine that can later be offered as part of the Meridian suite to regional clients." This is the revenue play we identified in the proposal analysis. It's already in the deck. Emphasize this — it transforms Arbor from a cost centre to a revenue generator.

---

## Gap Summary — What's Promised vs What's Built

| Deck Promise                       | Built?      | Gap                                               | Risk                               |
| ---------------------------------- | ----------- | ------------------------------------------------- | ---------------------------------- |
| Employee records & workflows       | **Yes**     | Offboarding workflow not automated as single flow | Low                                |
| Thai payroll (SSF, PIT)            | **No**      | SG payroll live; Thai calculators planned         | High — deck explicitly promises TH |
| Thai statutory leave types         | **No**      | SG leave live; Thai types planned                 | Medium                             |
| Thai legal advisory with citations | **No**      | SG advisory live; Thai KB planned                 | High — deck explicitly promises TH |
| Leave, claims, attendance, shifts  | **Yes**     | All live                                          | None                               |
| Performance reviews & skills       | **Yes**     | All live                                          | None                               |
| HR Co-Pilot (shadow agent)         | **Yes**     | All live                                          | None                               |
| PDPA compliance & security         | **Yes**     | All live, thoroughly tested                       | None                               |
| Multi-country architecture         | **Yes**     | Architecture proven with SG                       | None                               |
| Integration connectors             | **Partial** | Architecture built; external credentials needed   | Low — correctly labelled "Planned" |
| Mobile app                         | **Yes**     | Full Flutter app                                  | None                               |

### Bottom Line

**6 of 8 pillars are fully delivered.** Pillars 2 and 5 (Thai payroll and Thai legal advisory) are the gaps — and they're the PoC deliverables. The deck's "Suggested Next Steps" slide already positions these as next: "Confirm Thai Law Scope" and "Define a Go-Live Milestone."

The deck is well-crafted and honestly positioned. The features it promises as live ARE live. The features that need Thailand adaptation are either labelled as future or positioned as the next step. The only risk is if someone reads "Country-Aware Rules: Thai social security, tax withholding" as "this works today" rather than "this is what we're building."

---

## Recommendation for Friday's Meeting

1. **Use this deck as-is** — it's already tailored for Ricoh Thailand and Project Meridian
2. **Keep "Arbor" branding** if this deck has been shared — don't create confusion with "Central"
3. **The demo supplements the deck** — show the SG system working to prove Pillars 1, 3, 4, 6, 7 are real
4. **The CCO narrative** (from `10-ricoh-thailand-proposal-analysis.md`) adds the cultural layer (ringi/EATP, TQM/safety chain, kreng jai) that the deck doesn't cover
5. **The ask remains the same**: PoC for Pillars 2 and 5 (Thai payroll + Thai legal advisory), 4-6 weeks, validated by Thai legal counsel
