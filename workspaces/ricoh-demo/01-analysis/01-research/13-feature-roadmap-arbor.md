# Central HR Platform — Feature Roadmap by Module

**For**: Client presentation / slide deck material
**Date**: 2026-03-26

Status legend:

- **Live** — Production-ready, fully functional today
- **Planned** — Designed and scoped, to be built in next phase
- **Future** — On the roadmap, pending client engagement

---

## 1. Employee Management

| Feature                                          | Status      | Detail                                          |
| ------------------------------------------------ | ----------- | ----------------------------------------------- |
| Employee profiles (personal, contact, emergency) | **Live**    | Full CRUD with role-based access                |
| Salary components (base, allowances, deductions) | **Live**    | Multiple components per employee                |
| Employment history & events                      | **Live**    | Promotions, transfers, salary changes tracked   |
| Employee documents (upload, categorize)          | **Live**    | File upload with metadata                       |
| Org chart                                        | **Live**    | Hierarchical reporting structure                |
| CSV bulk import                                  | **Live**    | Import employees from spreadsheet               |
| Probation tracking with reminders                | **Live**    | Auto-calculated confirmation dates              |
| Family member records                            | **Live**    | Dependants for benefits/tax                     |
| Skills inventory                                 | **Live**    | Employee competency tracking                    |
| Custom fields (per-company)                      | **Live**    | Define company-specific employee fields         |
| Employee self-service portal                     | **Live**    | View profile, payslips, leave balances          |
| Onboarding workflow (invite → KET → credentials) | **Live**    | Email invitation with token-based registration  |
| Offboarding workflow with final salary calc      | **Planned** | Exit checklist, asset return, final pay         |
| Employee engagement surveys                      | **Future**  | Pulse surveys with analytics                    |
| Succession planning                              | **Future**  | Key person identification, readiness assessment |

---

## 2. Payroll

| Feature                                                            | Status      | Detail                                          |
| ------------------------------------------------------------------ | ----------- | ----------------------------------------------- |
| Gross-to-net calculation with statutory deductions                 | **Live**    | CPF, SDL, FWL, SHG auto-calculated              |
| Payroll run workflow (draft → calculate → review → approve → paid) | **Live**    | Multi-step with role-based approval             |
| Payslip generation (itemised, EA s88A compliant)                   | **Live**    | PDF generation and email delivery               |
| CPF e-Submit file generation                                       | **Live**    | CSV format for CPF Board portal upload          |
| Bank GIRO file generation                                          | **Live**    | Standard banking format for salary transfer     |
| IR8A / Appendix 8A tax filing data                                 | **Live**    | Annual tax filing for IRAS                      |
| IR21 (cessation of employment) filing                              | **Live**    | For departing foreign employees                 |
| Pay items (configurable allowances/deductions)                     | **Live**    | Company-specific pay components                 |
| Pay schemes (salary structures)                                    | **Live**    | Grouped pay item templates                      |
| Payroll variance reports                                           | **Live**    | Month-on-month comparison                       |
| Ad-hoc payroll runs (bonus, 13th month)                            | **Live**    | Separate from monthly cycle                     |
| Payroll simulation (what-if)                                       | **Live**    | Preview before committing                       |
| YTD tracking (per-employee)                                        | **Live**    | Year-to-date CPF, tax, earnings                 |
| Multi-currency payroll                                             | **Planned** | For regional offices with different currencies  |
| Thailand payroll (SSF, PIT withholding)                            | **Planned** | Thai Social Security + personal income tax      |
| Thailand statutory filing (SSO, PND 1)                             | **Planned** | Thai government submission formats              |
| Automated bank payment integration                                 | **Future**  | Direct API to bank for salary disbursement      |
| Payroll analytics dashboard                                        | **Future**  | Cost trends, headcount impact, budget vs actual |

---

## 3. Leave Management

| Feature                                                                 | Status      | Detail                                         |
| ----------------------------------------------------------------------- | ----------- | ---------------------------------------------- |
| Leave type configuration (13 types)                                     | **Live**    | Annual, sick, maternity, childcare, NS, etc.   |
| Leave application workflow (apply → approve/reject)                     | **Live**    | With manager approval chain                    |
| Leave balance auto-calculation by service years                         | **Live**    | EA progression: 7→14 days                      |
| Public holiday calendar (Singapore gazetted)                            | **Live**    | Auto-substitute when holiday falls on rest day |
| Leave policies (statutory + company)                                    | **Live**    | Configurable per company                       |
| Calendar view                                                           | **Live**    | Team leave calendar                            |
| Leave encashment                                                        | **Live**    | Convert unused leave to cash                   |
| Off-in-lieu tracking                                                    | **Live**    | Compensatory leave for work on holidays        |
| Prorated leave for mid-year joiners                                     | **Live**    | Auto-calculated based on join date             |
| Leave type configs (carry-forward rules)                                | **Live**    | Max carry-forward, expiry rules                |
| Employee self-service leave                                             | **Live**    | Apply, view balance, withdraw                  |
| Thailand leave types (6 days annual, 30 sick, 3 personal, 98 maternity) | **Planned** | Thai Labour Protection Act entitlements        |
| Team leave planning (conflict detection)                                | **Future**  | Alert when too many team members on leave      |
| Leave analytics (utilization rates, patterns)                           | **Future**  | Department-level insights                      |

---

## 4. Claims & Expenses

| Feature                                            | Status     | Detail                                   |
| -------------------------------------------------- | ---------- | ---------------------------------------- |
| Claim categories (transport, meals, medical, etc.) | **Live**   | Company-configurable                     |
| Claim submission with receipt upload               | **Live**   | Photo/document attachment                |
| Manager approval workflow                          | **Live**   | Multi-level approval chains              |
| Claim audit trail                                  | **Live**   | Full history of status changes           |
| Claim groups (batch processing)                    | **Live**   | Group claims for payroll integration     |
| Payroll-ready integration                          | **Live**   | Approved claims feed into next payroll   |
| Receipt OCR (auto-extract amount, vendor, date)    | **Future** | AI-powered receipt scanning              |
| Corporate card reconciliation                      | **Future** | Match card transactions to claims        |
| Per-diem rules by travel destination               | **Future** | Auto-calculate meal/transport allowances |

---

## 5. Attendance & Timesheets

| Feature                                 | Status      | Detail                                             |
| --------------------------------------- | ----------- | -------------------------------------------------- |
| Clock in/out (web)                      | **Live**    | One-click with timestamp                           |
| Daily attendance records                | **Live**    | Present, absent, late, half-day, on-leave, holiday |
| Overtime tracking and calculation       | **Live**    | Auto-calculate OT based on clock times             |
| Timesheet submission and approval       | **Live**    | Weekly/monthly timesheet workflow                  |
| Lateness tracking with thresholds       | **Live**    | Configurable grace period                          |
| Early departure tracking                | **Live**    | Configurable threshold                             |
| Attendance dashboard                    | **Live**    | Real-time attendance overview                      |
| Attendance correction/edit              | **Live**    | Manager can correct records                        |
| Mobile clock in/out                     | **Planned** | GPS-enabled mobile attendance                      |
| Geofencing                              | **Future**  | Restrict clock-in to office locations              |
| Biometric integration                   | **Future**  | Fingerprint/face recognition devices               |
| Attendance analytics (patterns, trends) | **Future**  | Department-level absence patterns                  |

---

## 6. Shift Scheduling

| Feature                                           | Status     | Detail                                          |
| ------------------------------------------------- | ---------- | ----------------------------------------------- |
| Shift templates (morning, afternoon, night, etc.) | **Live**   | Reusable shift definitions                      |
| Schedule creation and assignment                  | **Live**   | Assign employees to shifts                      |
| Schedule publishing                               | **Live**   | Notify employees of published schedule          |
| Employee availability tracking                    | **Live**   | Mark available/unavailable dates                |
| Hours tracking per employee                       | **Live**   | Total hours per period                          |
| Hourly rates and shift multipliers                | **Live**   | Night shift premium, holiday multiplier         |
| Self-service schedule view                        | **Live**   | Employees see their upcoming shifts             |
| Shift swap requests                               | **Future** | Employee-to-employee swap with approval         |
| Auto-scheduling (AI-optimized)                    | **Future** | Generate optimal schedules based on constraints |
| Demand forecasting                                | **Future** | Predict staffing needs from historical data     |

---

## 7. Recruitment

| Feature                                                    | Status     | Detail                                         |
| ---------------------------------------------------------- | ---------- | ---------------------------------------------- |
| Job listing creation (title, description, requirements)    | **Live**   | Full job posting management                    |
| Publish/close job listings                                 | **Live**   | Control listing visibility                     |
| Candidate tracking                                         | **Live**   | Application pipeline management                |
| Interview scheduling                                       | **Live**   | Schedule interviews with calendar integration  |
| Interview feedback collection                              | **Live**   | Structured interviewer feedback                |
| Offer management                                           | **Live**   | Generate and track offers                      |
| Hire-to-employee conversion                                | **Live**   | One-click convert candidate to employee record |
| Job board integration (JobStreet, LinkedIn)                | **Future** | Push listings to external boards               |
| AI resume screening                                        | **Future** | Auto-rank candidates against job requirements  |
| Recruitment analytics (time-to-hire, source effectiveness) | **Future** | Pipeline metrics                               |

---

## 8. Appraisals & Performance

| Feature                                    | Status     | Detail                              |
| ------------------------------------------ | ---------- | ----------------------------------- |
| Appraisal templates (criteria, weightings) | **Live**   | Configurable review forms           |
| Review periods (quarterly, annual)         | **Live**   | Cycle management                    |
| Launch review cycles company-wide          | **Live**   | Bulk initiation                     |
| Self-assessment                            | **Live**   | Employee self-review                |
| Manager review and scoring                 | **Live**   | Rating against criteria             |
| Submit and sign-off workflow               | **Live**   | Multi-step approval                 |
| 360-degree feedback                        | **Future** | Peer and subordinate reviews        |
| Goal/OKR management                        | **Future** | Objective tracking with key results |
| Performance improvement plans (PIP)        | **Future** | Structured improvement tracking     |
| Compensation review linked to performance  | **Future** | Merit-based salary adjustment       |

---

## 9. Projects & Costing

| Feature                                    | Status     | Detail                            |
| ------------------------------------------ | ---------- | --------------------------------- |
| Project CRUD (name, dates, budget, status) | **Live**   | Full project management           |
| Team assignments with roles                | **Live**   | Assign employees to project roles |
| Role-based hourly rates                    | **Live**   | Different rates per role          |
| Overhead allocation                        | **Live**   | Distribute shared costs           |
| Timesheet entries per project              | **Live**   | Track hours by project            |
| Cost calculation and reporting             | **Live**   | Budget vs actual                  |
| Resource allocation view                   | **Live**   | Who is assigned where             |
| Gantt chart timeline                       | **Future** | Visual project timeline           |
| Project profitability analysis             | **Future** | Revenue vs cost per project       |

---

## 10. Inventory & Asset Management

| Feature                                     | Status     | Detail                            |
| ------------------------------------------- | ---------- | --------------------------------- |
| Asset locations and categories              | **Live**   | Organize by office/type           |
| Asset items (serial number, value, status)  | **Live**   | Full asset register               |
| Reserve / issue / return / dispose workflow | **Live**   | Complete lifecycle                |
| Employee acknowledgment                     | **Live**   | Employee confirms receipt         |
| Asset request with approval                 | **Live**   | Request → manager approve → issue |
| Full asset history                          | **Live**   | Audit trail per item              |
| Depreciation tracking                       | **Future** | Auto-calculate asset depreciation |
| QR code / barcode scanning                  | **Future** | Mobile scan for quick lookup      |

---

## 11. Documents & Templates

| Feature                                         | Status      | Detail                                         |
| ----------------------------------------------- | ----------- | ---------------------------------------------- |
| Contract templates                              | **Live**    | Employment contract generation                 |
| Offer letter templates                          | **Live**    | Customizable offer letters                     |
| KET generation (Key Employment Terms, EA s95)   | **Live**    | Statutory requirement                          |
| Generate from template with employee data merge | **Live**    | Auto-fill employee details                     |
| Preview before generation                       | **Live**    | Review before committing                       |
| Download as DOCX                                | **Live**    | Standard document format                       |
| Thailand document templates (Thai language)     | **Planned** | Thai employment contracts, Thai KET equivalent |
| E-signature integration (DocuSign, Adobe Sign)  | **Future**  | Digital signing workflow                       |
| Document version control                        | **Future**  | Track changes across versions                  |

---

## 12. Compliance

| Feature                                             | Status      | Detail                                     |
| --------------------------------------------------- | ----------- | ------------------------------------------ |
| Compliance health check against SG employment law   | **Live**    | Category-by-category evaluation            |
| Compliance scoring per category                     | **Live**    | Percentage compliance with recommendations |
| Regulatory alert notifications                      | **Live**    | Push updates when laws change              |
| Compliance dashboard                                | **Live**    | Overview of compliance status              |
| Thailand compliance checks (LPA, SSA, Revenue Code) | **Planned** | Thai regulatory domain evaluation          |
| Compliance calendar (filing deadlines)              | **Future**  | Auto-generated deadline reminders          |
| Audit-ready compliance reports                      | **Future**  | Exportable for external auditors           |

---

## 13. Reports & Analytics

| Feature                             | Status     | Detail                          |
| ----------------------------------- | ---------- | ------------------------------- |
| Headcount by department (bar chart) | **Live**   | Visual breakdown                |
| Payroll cost trend (line chart)     | **Live**   | 3-6 month trending              |
| Leave utilization (stacked bar)     | **Live**   | By type and department          |
| Foreign worker ratio (donut chart)  | **Live**   | Quota compliance visual         |
| Payroll summary and YTD reports     | **Live**   | Exportable reports              |
| Claims analysis                     | **Live**   | By category and department      |
| Attendance patterns                 | **Live**   | Trends and anomalies            |
| Custom report builder               | **Future** | Drag-and-drop report creation   |
| Scheduled report delivery (email)   | **Future** | Auto-send reports on schedule   |
| Benchmark comparisons (industry)    | **Future** | Compare against sector averages |

---

## 14. AI Advisory Engine

| Feature                                           | Status      | Detail                                      |
| ------------------------------------------------- | ----------- | ------------------------------------------- |
| Natural language Q&A on Singapore employment law  | **Live**    | 6 regulatory domains                        |
| Real-time SSE streaming responses                 | **Live**    | Token-by-token streaming                    |
| Legal citations (Act, Section, subsection)        | **Live**    | Every claim traced to source                |
| 3-tier risk classification (GREEN / AMBER / RED)  | **Live**    | Calibrated to query sensitivity             |
| Deterministic calculator tool invocation          | **Live**    | AI triggers calculators, not guesses        |
| Multi-turn conversation with memory               | **Live**    | Context preserved across messages           |
| Professional referral for RED-tier queries        | **Live**    | Specific contacts and phone numbers         |
| Risk-appropriate disclaimers                      | **Live**    | Calibrated per risk tier                    |
| Conversation management (create, rename, delete)  | **Live**    | Organize advisory conversations             |
| Thailand employment law advisory (3 domains)      | **Planned** | Labour Protection Act, Social Security, Tax |
| Thailand employment law advisory (full 6 domains) | **Planned** | + Foreign Employment, Labour Relations, OSH |
| Bilingual advisory (Thai + English)               | **Planned** | Respond in query language                   |
| Malaysia employment law advisory                  | **Future**  | EA 1955, EPF/SOCSO/EIS                      |
| Vietnam employment law advisory                   | **Future**  | Labour Code 2019, Social Insurance          |
| Indonesia employment law advisory                 | **Future**  | Omnibus Law, BPJS                           |
| Philippines employment law advisory               | **Future**  | Labour Code, SSS/PhilHealth                 |

---

## 15. Calculators

| Calculator                                | SG Status | TH Status   | Detail                           |
| ----------------------------------------- | --------- | ----------- | -------------------------------- |
| Social security contributions (CPF / SSF) | **Live**  | **Planned** | All age bands, citizenship tiers |
| Leave entitlement by service years        | **Live**  | **Planned** | 13 types (SG), 7 types (TH)      |
| Overtime pay rates                        | **Live**  | **Planned** | 1.5x-3x scenarios                |
| Notice period by tenure                   | **Live**  | **Planned** | Statutory scale                  |
| Severance/retrenchment benefits           | **Live**  | **Planned** | Tenure-based calculation         |
| Foreign worker quota & levy               | **Live**  | N/A         | SG-specific DRC and levy rates   |
| Cost to company breakdown                 | **Live**  | **Planned** | Full employment cost             |
| Personal income tax withholding           | N/A       | **Planned** | Thai PIT annualization method    |
| Work permit ratio monitor (4:1)           | N/A       | **Planned** | Thai foreign worker compliance   |

---

## 16. Knowledge Base

| Feature                             | Status      | Detail                                     |
| ----------------------------------- | ----------- | ------------------------------------------ |
| Singapore Employment Act provisions | **Live**    | ~17 structured provisions                  |
| Singapore CPF Act provisions        | **Live**    | ~8 structured provisions                   |
| Singapore EFMA provisions           | **Live**    | ~8 structured provisions                   |
| Singapore TAFEP guidelines          | **Live**    | ~9 structured provisions                   |
| Singapore WSH Act provisions        | **Live**    | ~8 structured provisions                   |
| Singapore Tax/IRAS provisions       | **Live**    | ~7 structured provisions                   |
| Adversarial gap provisions          | **Live**    | ~32 provisions                             |
| Semantic search (vector embeddings) | **Live**    | Gemini text-embedding-004                  |
| Keyword search fallback             | **Live**    | When embeddings unavailable                |
| Cross-references between provisions | **Live**    | Mapped relationships                       |
| Practical examples per provision    | **Live**    | Worked scenarios                           |
| Historical rate tables              | **Live**    | CPF rates, levy rates with effective dates |
| Thailand Labour Protection Act      | **Planned** | ~20 key provisions                         |
| Thailand Social Security Act        | **Planned** | Contribution rates, benefits               |
| Thailand Revenue Code (PIT)         | **Planned** | Tax brackets, deductions                   |
| Thailand Foreign Employment Act     | **Planned** | Work permits, 4:1 ratio                    |
| Thailand Labour Relations Act       | **Planned** | Unions, collective bargaining              |
| Thailand OSH Act                    | **Planned** | Workplace safety                           |
| Malaysia Employment Act 1955        | **Future**  | Key provisions                             |
| Vietnam Labour Code 2019            | **Future**  | Key provisions                             |

---

## 17. Trust & Safety

| Feature                                                 | Status      | Detail                         |
| ------------------------------------------------------- | ----------- | ------------------------------ |
| 13-step safety chain                                    | **Live**    | Every query, every time        |
| EATP trust lineage (genesis, attestations, constraints) | **Live**    | Cryptographic audit trail      |
| Prompt injection screening (8+ patterns)                | **Live**    | Deterministic detection        |
| Circumvention detection (10+ SG patterns)               | **Live**    | "How to avoid paying CPF" etc. |
| Scope screening (is this an HR question?)               | **Live**    | LLM-based classifier           |
| Risk-tier classification (GREEN/AMBER/RED)              | **Live**    | Per-response risk level        |
| Citation validation (do cited provisions exist?)        | **Live**    | Post-generation verification   |
| Response screening (TAFEP compliance)                   | **Live**    | Discriminatory content check   |
| Rate limiting (per-user, per-company)                   | **Live**    | Bounded request counts         |
| Budget management (monthly spending cap)                | **Live**    | Per-company LLM budget         |
| Thailand circumvention patterns                         | **Planned** | Thai-law-specific detection    |
| Anti-hallucination reinforcement                        | **Future**  | Enhanced grounding techniques  |

---

## 18. Shadow Agent

| Feature                                          | Status     | Detail                                         |
| ------------------------------------------------ | ---------- | ---------------------------------------------- |
| Page-aware contextual intelligence               | **Live**   | Knows which page, what data visible            |
| Natural language intent classification           | **Live**   | "Approve John's leave" → action                |
| PACE safety model (Preview-Approve-Confirm-Exit) | **Live**   | AI never acts without human approval           |
| Entity resolution ("John" → employee record)     | **Live**   | Name-to-ID mapping                             |
| Multi-step workflow composition                  | **Live**   | Complex commands broken into API calls         |
| Proactive morning briefing cards                 | **Live**   | Pending approvals, expiring permits, deadlines |
| Page-aware contextual nudges                     | **Live**   | "3 leave requests pending" on leave page       |
| Behavioral observation and learning              | **Live**   | Tracks usage patterns over time                |
| Memory persistence                               | **Live**   | Remembers user patterns across sessions        |
| Action history with undo                         | **Live**   | View and reverse past actions                  |
| Predictive suggestions based on patterns         | **Future** | "You usually run payroll on the 25th"          |
| Voice command interface                          | **Future** | Speak commands to shadow agent                 |

---

## 19. Integrations (MCP Architecture)

| Integration                                                                  | Status      | Detail                                   |
| ---------------------------------------------------------------------------- | ----------- | ---------------------------------------- |
| **Infrastructure** (circuit breakers, retry, idempotency, PII filter, audit) | **Live**    | Production-grade adapter framework       |
| MOM (Ministry of Manpower)                                                   | **Planned** | Work pass status, levy queries           |
| IRAS (tax authority)                                                         | **Planned** | Auto Income Submission, tax queries      |
| CPF Board                                                                    | **Planned** | Contribution submission, balance queries |
| ACRA (business registry)                                                     | **Planned** | Company verification                     |
| MyInfo / Singpass                                                            | **Planned** | National identity verification           |
| SkillsFuture                                                                 | **Planned** | Training credit queries                  |
| data.gov.sg                                                                  | **Planned** | Public dataset access                    |
| Xero (accounting)                                                            | **Planned** | Payroll journal sync, invoice generation |
| QuickBooks (accounting)                                                      | **Planned** | Same as Xero                             |
| Financio (SG accounting)                                                     | **Planned** | Local accounting integration             |
| Zoho Books                                                                   | **Planned** | Accounting sync                          |
| PayNow (instant payment)                                                     | **Planned** | QR code salary payment                   |
| GIRO (bank transfer)                                                         | **Planned** | Batch salary transfer                    |
| Wise (international)                                                         | **Planned** | Cross-border salary payments             |
| Aspire (business banking)                                                    | **Planned** | Corporate card, expense management       |
| Slack                                                                        | **Planned** | Notifications, approvals via Slack       |
| Telegram                                                                     | **Planned** | Bot notifications, regulatory monitoring |
| WhatsApp Business                                                            | **Planned** | Employee notifications                   |
| Microsoft Teams                                                              | **Planned** | Approval cards, notifications            |
| Email (Resend / AWS SES)                                                     | **Planned** | Transactional email delivery             |
| SMS                                                                          | **Planned** | Urgent notifications                     |
| Google Calendar                                                              | **Planned** | Leave sync to calendar                   |
| AWS S3 (document storage)                                                    | **Planned** | Cloud document storage                   |
| Talenox (HRIS sync)                                                          | **Future**  | Data migration from Talenox              |
| HREasily (HRIS sync)                                                         | **Future**  | Data migration from HREasily             |
| Thailand SSO (Social Security Office)                                        | **Future**  | Thai contribution submission             |
| Thailand Revenue Department                                                  | **Future**  | Thai tax filing                          |

---

## 20. Security & Auth

| Feature                                               | Status     | Detail                                   |
| ----------------------------------------------------- | ---------- | ---------------------------------------- |
| JWT authentication (register, login, refresh, logout) | **Live**   | bcrypt password hashing                  |
| Google OAuth SSO                                      | **Live**   | One-click Google sign-in                 |
| Employee invitation registration                      | **Live**   | Token-based with 7-day expiry            |
| Multi-tenant isolation (company_id scope)             | **Live**   | Enforced at API layer                    |
| BYOK multi-provider LLM config                        | **Live**   | 7 providers, encrypted storage           |
| Per-company LLM budget management                     | **Live**   | Monthly cap with usage tracking          |
| Per-user LLM config override                          | **Live**   | User-level provider preference           |
| Field encryption (NRIC, bank accounts)                | **Live**   | Fernet encryption at rest                |
| LLM API key encryption                                | **Live**   | BYOK keys encrypted before DB storage    |
| PDPA compliance (access logging, consent)             | **Live**   | Audit trail for data access              |
| Rate limiting (auth + advisory)                       | **Live**   | Per-IP and per-user limits               |
| Input validation (NaN, injection, length)             | **Live**   | Comprehensive sanitization               |
| SAML SSO                                              | **Future** | Enterprise identity provider integration |
| MFA (multi-factor authentication)                     | **Future** | TOTP or SMS second factor                |
| IP allowlisting                                       | **Future** | Restrict access by IP range              |
| SSO with Azure AD                                     | **Future** | Microsoft enterprise SSO                 |

---

## 21. Mobile App (Flutter)

| Feature                                         | Status      | Detail                             |
| ----------------------------------------------- | ----------- | ---------------------------------- |
| Advisory chat with SSE streaming                | **Live**    | Full advisory on mobile            |
| 7 statutory calculators (native Dart)           | **Live**    | Run on-device, no API needed       |
| Compliance checker                              | **Live**    | Category-by-category assessment    |
| Document browsing and generation                | **Live**    | View and generate templates        |
| Emergency HR guides                             | **Live**    | Crisis response on the go          |
| Regulatory alerts                               | **Live**    | Push notification ready            |
| Analytics dashboard                             | **Live**    | Key metrics at a glance            |
| Auth (login, signup, forgot password)           | **Live**    | Full auth flow                     |
| Onboarding wizard                               | **Live**    | Guided first-run                   |
| Employee self-service (leave, claims, payslips) | **Planned** | Full self-service on mobile        |
| Mobile attendance (GPS clock in/out)            | **Planned** | Location-verified attendance       |
| Push notifications                              | **Planned** | Approval requests, alerts          |
| Offline mode                                    | **Future**  | Core features without connectivity |
| Biometric login (Face ID, fingerprint)          | **Future**  | Native device authentication       |

---

## 22. Admin & QA

| Feature                                                    | Status     | Detail                               |
| ---------------------------------------------------------- | ---------- | ------------------------------------ |
| Admin dashboard (regulatory updates, staleness monitoring) | **Live**   | Platform-level oversight             |
| QA evaluation sessions                                     | **Live**   | Review and rate advisory responses   |
| Instruction patches (propose → test → approve → deploy)    | **Live**   | Improve advisory quality iteratively |
| KB management (provision/act/domain CRUD)                  | **Live**   | Full knowledge base administration   |
| Conversation browser                                       | **Live**   | Review all advisory conversations    |
| Learning pipeline (feedback → gaps → recommendations)      | **Live**   | Continuous improvement cycle         |
| Integration health monitoring                              | **Live**   | MCP adapter status dashboard         |
| Monthly quality reports                                    | **Live**   | Advisory accuracy metrics            |
| A/B testing for advisory improvements                      | **Future** | Compare instruction variants         |
| Customer success dashboard                                 | **Future** | Cross-company usage analytics        |

---

## Jurisdiction Expansion Roadmap

| Jurisdiction    | KB                                          | Calculators                     | Specialists                     | Filing Formats                      | Timeline                            |
| --------------- | ------------------------------------------- | ------------------------------- | ------------------------------- | ----------------------------------- | ----------------------------------- |
| **Singapore**   | **Live** (89+ provisions, 6 domains)        | **Live** (7 calculators)        | **Live** (7 specialists)        | **Live** (CPF e-Submit, IR8A, IR21) | Now                                 |
| **Thailand**    | **Planned** (20+ provisions, 3 domains → 6) | **Planned** (3 → 5 calculators) | **Planned** (3 → 6 specialists) | **Planned** (SSO, PND 1)            | 4-6 weeks (PoC) → 8-12 weeks (full) |
| **Malaysia**    | **Future**                                  | **Future**                      | **Future**                      | **Future**                          | 4-6 weeks per jurisdiction          |
| **Vietnam**     | **Future**                                  | **Future**                      | **Future**                      | **Future**                          | (leveraging proven architecture)    |
| **Indonesia**   | **Future**                                  | **Future**                      | **Future**                      | **Future**                          |                                     |
| **Philippines** | **Future**                                  | **Future**                      | **Future**                      | **Future**                          |                                     |

---

## Summary Counts

| Category               | Live      | Planned | Future          | Total    |
| ---------------------- | --------- | ------- | --------------- | -------- |
| HRIS module features   | 142       | 12      | 31              | 185      |
| Calculators            | 7 (SG)    | 9 (TH)  | 2               | 18       |
| KB domains             | 6 (SG)    | 6 (TH)  | 8 (MY/VN/ID/PH) | 20       |
| Advisory jurisdictions | 1 (SG)    | 1 (TH)  | 4 (ASEAN)       | 6        |
| Integrations           | 1 (infra) | 24      | 4               | 29       |
| Security features      | 12        | 0       | 4               | 16       |
| Mobile features        | 9         | 3       | 2               | 14       |
| **Total features**     | **~178**  | **~55** | **~51**         | **~284** |
