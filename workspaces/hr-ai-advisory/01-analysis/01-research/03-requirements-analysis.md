# Requirements Analysis: AI-Powered HR Advisory Platform for Singapore SMEs

## Executive Summary

- **Product**: AI-powered HR advisory platform for Singapore SME owners
- **Complexity**: High (multi-domain regulatory knowledge, contextual personalization, legal accuracy requirements)
- **Risk Level**: High (incorrect legal/regulatory advice carries real consequences for users)
- **Estimated Effort**: 16-24 weeks for MVP, phased delivery
- **Primary Value Proposition**: Democratize access to specialist-grade HR advisory that only large enterprises can currently afford

---

## 1. User Personas and Journeys

### Persona A: "The Accidental HR Manager" -- SME Owner (5-20 employees)

**Profile**: Rachel Tan, 38. Owns a digital marketing agency with 12 employees. No HR training. Handles HR decisions herself alongside running the business. Currently relies on Google searches, WhatsApp groups with other SME owners, and occasional calls to MOM hotline. Has been fined once for a CPF contribution error she did not know she was making.

**Pain Points**:

- Does not know what she does not know (unknown unknowns)
- Spends 4-6 hours/week on HR admin that she is not qualified to do
- Anxious about compliance -- worries she is violating rules she has never heard of
- Cannot afford a dedicated HR person or consultant ($3-5K/month)
- Gets conflicting advice from different sources

**Top 10 Questions/Tasks**:

| #   | Question/Task                                                                                                                | Urgency | Complexity | Domain           |
| --- | ---------------------------------------------------------------------------------------------------------------------------- | ------- | ---------- | ---------------- |
| 1   | "I need to hire my first foreign worker. What passes are available, what are the quotas, and what will it actually cost me?" | High    | High       | Foreign Manpower |
| 2   | "An employee says she's pregnant. What are my obligations? How much maternity leave? Who pays?"                              | High    | Medium     | Leave (CDCSA)    |
| 3   | "I want to fire someone who isn't performing. What's the process so I don't get sued?"                                       | High    | High       | Termination      |
| 4   | "How much CPF do I contribute for each employee? It seems different for different ages."                                     | High    | Medium     | CPF              |
| 5   | "I need a proper employment contract. Can you generate one that's legally compliant?"                                        | Medium  | Medium     | Contracts        |
| 6   | "An employee wants to work from home 2 days a week. Do I have to allow it?"                                                  | Medium  | Medium     | FWA              |
| 7   | "My employee had an accident at work. What do I do? What forms do I file?"                                                   | High    | High       | WSH, Work Injury |
| 8   | "What's the minimum number of days annual leave I must give?"                                                                | Low     | Low        | Leave (EA)       |
| 9   | "I want to give year-end bonuses. Are there CPF implications? Any tax issues?"                                               | Medium  | Medium     | CPF, Payroll/Tax |
| 10  | "Am I covered by the Employment Act? Some of my staff earn over $4,500."                                                     | Medium  | Medium     | EA Coverage      |

**Success Criteria**: Rachel gets a clear, accurate answer within 2 minutes. She feels confident acting on it. She does not need a second opinion from a lawyer for routine matters.

**Journey Map**:

1. Signs up, enters basic company info (sector, headcount, worker nationalities)
2. Asks first question in plain English / Singlish
3. Gets structured answer: what the law says, what it means for her specifically, what to do step by step
4. Downloads a template or form if needed
5. Returns whenever a new HR situation arises (reactive use)
6. Receives alerts when regulations change that affect her company

### Persona B: "The Scaling Founder" -- SME Owner (20-100 employees, crossing thresholds)

**Profile**: David Lim, 45. Runs a F&B chain with 65 employees across 4 outlets. Crossing regulatory thresholds he does not fully understand. Has a part-time bookkeeper who handles payroll but not HR compliance. Recently hit the 25-employee mark where some tripartite guidelines kick in. Employs a mix of locals, PRs, and foreign workers on various pass types.

**Pain Points**:

- Hitting headcount thresholds that trigger new obligations (25, 50 employees)
- Complex foreign worker quota and levy calculations across multiple outlets
- Managing different employment terms for different worker categories
- Needs to formalize HR policies that were previously informal
- Union awareness -- some of his workers may be unionized

**Top 10 Questions/Tasks**:

| #   | Question/Task                                                                                                                        | Urgency | Complexity | Domain                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------ | ------- | ---------- | ---------------------- |
| 1   | "I'm at 65 employees now. What obligations kicked in that I might not know about? What's coming at 100?"                             | High    | High       | Compliance Thresholds  |
| 2   | "I have 15 WP holders, 8 S Pass holders, and 42 locals/PRs across 4 F&B outlets. Am I within quota? What are my levies?"             | High    | High       | Foreign Manpower       |
| 3   | "I need a complete employee handbook. Can you generate one for an F&B company my size?"                                              | Medium  | High       | Policy Development     |
| 4   | "I'm retrenching 5 people due to closing one outlet. What's the process and what do I owe them?"                                     | High    | High       | Retrenchment           |
| 5   | "One of my cooks works split shifts. How do I calculate overtime and rest day pay correctly?"                                        | Medium  | High       | Working Hours/OT       |
| 6   | "I want to sponsor an EP for a head chef. What are the current salary requirements and how does Fair Consideration Framework apply?" | High    | High       | Foreign Manpower, FCF  |
| 7   | "I need to transfer 3 employees from one outlet entity to another. What are the rules?"                                              | Medium  | High       | Transfer of Employment |
| 8   | "How do I set up a proper performance management system? I've been doing it informally."                                             | Medium  | Medium     | Performance Management |
| 9   | "A former employee filed a complaint with TADM. What do I do? What's the process?"                                                   | High    | High       | Dispute Resolution     |
| 10  | "I'm collecting employee data for a new HR system. What are my PDPA obligations?"                                                    | Medium  | Medium     | Data Protection        |

**Success Criteria**: David gets advice that accounts for his specific company profile -- sector, size, worker mix. He understands threshold obligations proactively, not after a violation.

**Journey Map**:

1. Sets up detailed company profile (multiple outlets, worker breakdown by pass type and outlet)
2. Runs compliance health check ("Am I compliant across the board?")
3. Gets prioritized list of gaps and risks
4. Works through issues one by one with guided workflows
5. Generates required policies and documents
6. Uses calculators for quota/levy scenarios before hiring decisions
7. Receives proactive alerts on threshold changes and regulatory updates

### Persona C: "The Solo HR Warrior" -- HR Manager in SME

**Profile**: Priya Nair, 32. Sole HR person for a tech company with 45 employees. Has IHRP certification (CP level). Knows the basics but needs specialist-level backup on complex matters. Spends too much time on operational HR and not enough on strategic initiatives. Her boss expects her to know everything.

**Pain Points**:

- Expected to be an expert on everything from CPF to workplace safety to data protection
- No HR colleague to consult or sanity-check decisions with
- Needs to produce professional documents quickly (policies, letters, reports)
- Keeps up with regulatory changes manually (reading MOM circulars, tripartite advisories)
- Needs to justify HR recommendations to management with authoritative references

**Top 10 Questions/Tasks**:

| #   | Question/Task                                                                                                             | Urgency | Complexity | Domain                    |
| --- | ------------------------------------------------------------------------------------------------------------------------- | ------- | ---------- | ------------------------- |
| 1   | "Draft a termination letter for misconduct that's legally defensible. The employee was caught falsifying expense claims." | High    | High       | Termination, Document Gen |
| 2   | "What's the latest on the Workplace Fairness Legislation? How should we prepare?"                                         | Medium  | High       | Anti-discrimination       |
| 3   | "I need to update our leave policy to comply with the new paternity leave changes. Generate the updated policy."          | Medium  | Medium     | Leave, Policy Development |
| 4   | "An employee claims they're being harassed by a supervisor. Walk me through the investigation process step by step."      | High    | High       | Grievance Handling        |
| 5   | "We want to implement a flexible benefits scheme. What are the CPF and tax implications of different benefit types?"      | Medium  | High       | Benefits, CPF, Tax        |
| 6   | "Generate a comparison of S Pass vs EP for a candidate earning $4,800. Include all costs to company."                     | Medium  | Medium     | Foreign Manpower          |
| 7   | "I need to prepare for an MOM inspection. What do they typically check? What records must I have?"                        | High    | Medium     | Compliance                |
| 8   | "An employee on probation isn't working out. Is the termination process different during probation?"                      | Medium  | Medium     | Termination               |
| 9   | "We're introducing a commission scheme. How does it interact with overtime calculations and CPF?"                         | Medium  | High       | Wages, CPF, OT            |
| 10  | "Pull up the tripartite guidelines on managing excess manpower. I need to present options to management."                 | Medium  | Medium     | Retrenchment, Guidelines  |

**Success Criteria**: Priya gets specialist-depth answers with references to specific legislation/guidelines she can cite. She generates professional documents in minutes instead of hours. She stays current on regulatory changes without manual research.

**Journey Map**:

1. Sets up company profile with detailed employee demographics
2. Uses as daily reference tool for complex questions
3. Generates documents and policies with company-specific details auto-filled
4. Cross-references advice against official sources (needs citation links)
5. Receives regulatory update digests relevant to her company
6. Uses calculators and scenario tools for management presentations
7. Tracks compliance status across all domains

### Persona D: "The Efficiency Multiplier" -- HR Consultant

**Profile**: James Koh, 50. Independent HR consultant serving 8-12 SME clients at any time. IHRP-MP certified. Deep expertise but needs to serve multiple clients efficiently. Currently maintains his own templates and reference materials. Charges $150-250/hour and needs to maximize productive time.

**Pain Points**:

- Manages multiple client contexts simultaneously
- Needs to stay current across all domains for all client sectors
- Creates similar documents repeatedly with client-specific variations
- Time spent on research is time not billed to clients
- Needs to provide authoritative, well-sourced advice quickly

**Top 10 Questions/Tasks**:

| #   | Question/Task                                                                                                                              | Urgency | Complexity | Domain                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------- | ---------- | ------------------------ |
| 1   | "Switch to Client X's profile. They're a construction company with 200 workers, 150 on WP. Run a full compliance audit."                   | High    | High       | Multi-client, Compliance |
| 2   | "Draft an employment contract for Client Y (retail, 30 employees) for a part-time sales associate."                                        | Medium  | Medium     | Contracts, Document Gen  |
| 3   | "Client Z is restructuring. Generate a retrenchment package comparison -- statutory minimum vs market practice for their sector and size." | High    | High       | Retrenchment             |
| 4   | "What changed in MOM regulations this quarter that affects my F&B clients?"                                                                | Medium  | Medium     | Regulatory Updates       |
| 5   | "Client A wants to convert 5 WP holders to S Pass. Model the quota and levy impact."                                                       | Medium  | High       | Foreign Manpower         |
| 6   | "Generate a complete HR policy manual for a new client -- logistics company, 80 employees, unionized."                                     | Medium  | High       | Policy Development       |
| 7   | "A client's employee is claiming constructive dismissal. Outline the legal position and recommended response."                             | High    | High       | Termination, Dispute     |
| 8   | "Compare my 3 manufacturing clients' leave policies against statutory requirements and market benchmarks."                                 | Medium  | Medium     | Leave, Benchmarking      |
| 9   | "Draft a Fair Consideration Framework-compliant job advertisement for a senior finance role with EP."                                      | Medium  | Medium     | FCF, Foreign Manpower    |
| 10  | "Generate a monthly HR compliance report for Client B covering all outstanding items."                                                     | Medium  | Medium     | Compliance, Reporting    |

**Success Criteria**: James can switch between client contexts seamlessly. He generates client-ready documents in minutes. He spots compliance gaps across his portfolio efficiently. The platform pays for itself within the first month through time saved.

**Journey Map**:

1. Sets up multiple client profiles with detailed company information
2. Switches between client contexts for advice and document generation
3. Runs compliance audits per client on a schedule
4. Generates client-ready documents and reports
5. Tracks regulatory changes filtered by client relevance
6. Uses scenario modeling tools for client advisory sessions
7. Exports advice with references for client presentations

---

## 2. Feature Requirements

### 2.1 Advisory Engine

**Purpose**: The core intelligence layer. Users ask questions in natural language and receive accurate, contextualized HR advisory.

| Req ID  | Requirement              | Description                                                                                                      | Priority |
| ------- | ------------------------ | ---------------------------------------------------------------------------------------------------------------- | -------- |
| ADV-001 | Natural Language Q&A     | Accept questions in plain English (including Singlish patterns) and return structured advisory                   | P0       |
| ADV-002 | Context-Aware Responses  | All advice must be filtered through the user's company profile (sector, size, worker mix)                        | P0       |
| ADV-003 | Source Citations         | Every piece of legal/regulatory advice must cite the specific Act, section, guideline, or circular               | P0       |
| ADV-004 | Confidence Indicators    | Display confidence level. Flag when advice may be ambiguous or when professional consultation is recommended     | P0       |
| ADV-005 | Multi-turn Conversations | Support follow-up questions that maintain context from earlier in the conversation                               | P1       |
| ADV-006 | Scenario Comparison      | "What if" analysis: compare outcomes under different scenarios (e.g., "What if I hire on WP vs S Pass?")         | P1       |
| ADV-007 | Proactive Flagging       | When answering a question, flag related compliance risks the user may not have asked about                       | P1       |
| ADV-008 | Distinction Markers      | Clearly distinguish between: legal requirement, tripartite guideline, best practice, and platform recommendation | P0       |
| ADV-009 | Precedent References     | Where relevant, reference notable TADM/ECT cases or MOM enforcement actions                                      | P2       |
| ADV-010 | Bilingual Support        | Support queries and responses in English and Mandarin (future: Malay, Tamil)                                     | P2       |

**Edge Cases**:

- Question spans multiple regulatory domains (e.g., terminating a pregnant foreign worker -- touches termination, CDCSA, foreign manpower, and anti-discrimination)
- Laws conflict or are ambiguous (e.g., tripartite guideline says one thing, common practice says another)
- Question is about an area where the law is changing (pending legislation vs current law)
- Company profile is incomplete -- must still provide useful advice while flagging what's missing
- Question is outside scope (tax planning, immigration beyond work passes, commercial law)

### 2.2 Knowledge Base

**Purpose**: The structured repository of all regulatory content that powers the advisory engine.

| Req ID | Requirement                | Description                                                                                                    | Priority |
| ------ | -------------------------- | -------------------------------------------------------------------------------------------------------------- | -------- |
| KB-001 | Comprehensive Coverage     | All Singapore employment legislation, subsidiary legislation, tripartite guidelines, MOM advisories, CPF rules | P0       |
| KB-002 | Structured Taxonomy        | Content organized by domain, sub-topic, applicability (who it covers, who it exempts)                          | P0       |
| KB-003 | Cross-References           | Links between related provisions across different Acts and guidelines                                          | P0       |
| KB-004 | Version History            | Track changes to regulations over time. Show what changed, when, and what was replaced                         | P1       |
| KB-005 | Effective Dates            | Every provision tagged with effective date and, where known, sunset date                                       | P0       |
| KB-006 | Applicability Rules        | Each provision tagged with who it applies to (EA-covered vs non-EA, employee size thresholds, sector-specific) | P0       |
| KB-007 | Plain Language Summaries   | Every legal provision has a plain-language summary alongside the formal text                                   | P1       |
| KB-008 | Searchable                 | Full-text search with filtering by domain, applicability, effective date                                       | P1       |
| KB-009 | Authoritative Source Links | Link to official gazette, MOM website, CPF website for every provision                                         | P0       |
| KB-010 | Practical Examples         | Each provision includes practical examples of application (especially for complex calculations)                | P1       |

**Content Scope** (the actual regulatory corpus):

- Employment Act (Cap 91) and subsidiary legislation
- Child Development Co-Savings Act (CDCSA) -- maternity, paternity, childcare, adoption leave
- Central Provident Fund Act and regulations
- Employment of Foreign Manpower Act (EFMA)
- Work Injury Compensation Act (WICA)
- Workplace Safety and Health Act (WSHA) and subsidiary legislation
- Employment Claims Act
- Retirement and Re-employment Act (RRA)
- Personal Data Protection Act (PDPA) -- employment context
- All Tripartite Guidelines (FWA, retrenchment, salary, non-discriminatory job ads, wrongful dismissal, managing excess manpower, etc.)
- TAFEP Guidelines
- MOM Circulars and Advisories
- CPF Board Circulars
- Trade union legislation (Industrial Relations Act, Trade Unions Act)
- Upcoming: Workplace Fairness Legislation (anticipated 2025-2026)

### 2.3 Template Library

**Purpose**: Ready-to-use, legally compliant templates that users can customize for their company.

| Req ID | Requirement                | Description                                                                                                                                   | Priority |
| ------ | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| TL-001 | Employment Contracts       | Full-time, part-time, fixed-term, casual. EA-covered and non-EA variants                                                                      | P0       |
| TL-002 | HR Policy Templates        | Leave policy, disciplinary policy, grievance policy, FWA policy, anti-harassment policy, data protection policy, IT usage policy              | P0       |
| TL-003 | Letters                    | Offer letters, confirmation letters, warning letters, termination letters, retrenchment letters, reference letters, salary adjustment letters | P0       |
| TL-004 | Forms                      | Leave application, claims forms, FWA request forms, exit interview forms, performance review forms, incident report forms                     | P1       |
| TL-005 | Checklists                 | Onboarding checklist, offboarding checklist, MOM inspection readiness checklist, workplace safety checklist                                   | P1       |
| TL-006 | Guides                     | Step-by-step guides for common processes (hiring, termination, retrenchment, work injury reporting, TADM mediation preparation)               | P1       |
| TL-007 | Employee Handbook Template | Comprehensive handbook customizable by company profile                                                                                        | P1       |
| TL-008 | Payroll Templates          | Itemised payslip template (EA-compliant), key employment terms (KET) template                                                                 | P0       |
| TL-009 | Foreign Worker Templates   | IPA application support documents, work pass renewal checklists, security bond templates                                                      | P1       |
| TL-010 | Template Versioning        | Templates tagged with the regulatory version they comply with. Alert when a template is outdated                                              | P1       |

**Template Quality Requirements**:

- Every template must cite the regulatory basis (e.g., "This contract includes clauses required by Employment Act s95 and MOM's Key Employment Terms requirements")
- Templates must include guidance notes explaining each section
- Templates must be downloadable in editable formats (DOCX, PDF)
- Templates must be customizable with company profile data auto-filled

### 2.4 Company Profile

**Purpose**: The context engine that personalizes all advisory and document generation.

| Req ID | Requirement                    | Description                                                                                                                         | Priority |
| ------ | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- | -------- |
| CP-001 | Company Details                | Company name, UEN, registered address, incorporation date                                                                           | P0       |
| CP-002 | Industry Classification        | SSIC code, sector (services, manufacturing, construction, marine, process), sub-sector                                              | P0       |
| CP-003 | Headcount                      | Total employees, broken down by citizenship status (citizen, PR, foreigner) and pass type (WP, S Pass, EP, PEP, ONE Pass)           | P0       |
| CP-004 | Employee Demographics          | Age distribution (for CPF tier calculations), salary ranges (for EA coverage determination)                                         | P1       |
| CP-005 | Multi-Entity Support           | Companies with multiple entities or outlets can maintain separate profiles with consolidated view                                   | P1       |
| CP-006 | Worker Quota Dashboard         | Real-time quota utilization and available headroom per pass type                                                                    | P0       |
| CP-007 | Regulatory Applicability Map   | Based on profile, show which regulations apply and which do not                                                                     | P1       |
| CP-008 | Threshold Tracker              | Track proximity to headcount thresholds that trigger new obligations (e.g., 10, 25, 50 employees for various tripartite guidelines) | P1       |
| CP-009 | Union Status                   | Whether any employees are covered by collective agreements                                                                          | P2       |
| CP-010 | Profile-Driven Personalization | All advisory, templates, and calculations automatically use company profile data                                                    | P0       |

**Company Profile Data Model** (key fields):

```
Company Profile:
  - company_name: string
  - uen: string
  - ssic_code: string
  - sector: enum [services, manufacturing, construction, marine, process, other]
  - sub_sector: string
  - incorporation_date: date
  - financial_year_end: date
  - registered_address: string
  - outlets/branches: [Location]
  - union_status: enum [no_union, house_union, industry_union]
  - collective_agreement: boolean

Workforce:
  - total_headcount: int
  - citizens: int
  - prs: int
  - foreigners_wp: int
  - foreigners_spass: int
  - foreigners_ep: int
  - foreigners_pep: int
  - foreigners_onepass: int
  - age_distribution: {tier: count}  # for CPF
  - salary_ranges: {range: count}    # for EA coverage
  - ea_covered_count: int
  - non_ea_covered_count: int
```

### 2.5 Compliance Checker

**Purpose**: Proactive compliance assessment. "Tell me what I'm doing wrong before MOM does."

| Req ID | Requirement            | Description                                                                                                                                    | Priority |
| ------ | ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| CC-001 | Full Compliance Audit  | Comprehensive check across all regulatory domains based on company profile                                                                     | P1       |
| CC-002 | Domain-Specific Checks | Targeted checks for specific areas (e.g., "Check my leave policy compliance")                                                                  | P0       |
| CC-003 | Document Review        | Upload existing contracts/policies for compliance review against current regulations                                                           | P1       |
| CC-004 | Gap Analysis           | Identify what's missing (e.g., "You have no FWA policy -- new tripartite guidelines recommend one for companies with 25+ employees")           | P1       |
| CC-005 | Risk Scoring           | Rate compliance risks: Critical (legal violation), High (guideline non-compliance), Medium (best practice gap), Low (optimization opportunity) | P1       |
| CC-006 | Remediation Guidance   | For each gap, provide specific remediation steps with timeline                                                                                 | P1       |
| CC-007 | Compliance History     | Track compliance status over time. Show improvements and outstanding items                                                                     | P2       |
| CC-008 | Inspection Readiness   | "Am I ready for an MOM inspection?" checklist based on company profile                                                                         | P1       |

### 2.6 Calculator Tools

**Purpose**: Numerical tools for common HR calculations where errors are costly.

| Req ID | Requirement                     | Description                                                                                                                  | Priority |
| ------ | ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------- |
| CA-001 | CPF Calculator                  | Full CPF contribution calculator: employer + employee shares, by age tier, citizenship status, wage ceiling                  | P0       |
| CA-002 | Foreign Worker Levy Calculator  | Levy rates by pass type, sector, tier (basic/higher), and qualification                                                      | P0       |
| CA-003 | Quota Calculator                | DRC/S Pass quota calculation based on sector and local workforce                                                             | P0       |
| CA-004 | Leave Entitlement Calculator    | Annual leave, sick leave, maternity/paternity, childcare leave -- based on years of service, EA coverage, number of children | P0       |
| CA-005 | Overtime Calculator             | OT pay calculation including rest day, public holiday scenarios, monthly-rated vs hourly-rated                               | P1       |
| CA-006 | Notice Period Calculator        | Statutory and contractual notice periods, payment in lieu calculation                                                        | P1       |
| CA-007 | Retrenchment Benefit Calculator | Statutory minimum (if applicable), market norm by sector and years of service                                                | P1       |
| CA-008 | Cost-to-Company Calculator      | Total employment cost: salary + CPF + levy + insurance + benefits                                                            | P1       |
| CA-009 | Salary Benchmark                | Salary ranges by role and sector (sourced from MOM surveys where available)                                                  | P2       |
| CA-010 | Scenario Modeler                | "What if" calculator: model hiring scenarios and see quota, levy, CPF impact                                                 | P1       |

**Accuracy Requirements for Calculators**:

- CPF rates must match CPF Board published rates exactly (zero tolerance for error)
- Levy rates must match MOM published rates exactly
- Quota calculations must use current ratios published by MOM
- All calculators must show the date of the rates used and flag if rates may have changed

### 2.7 Update Alerts

**Purpose**: Keep users current on regulatory changes that affect their specific situation.

| Req ID | Requirement             | Description                                                                                                                     | Priority |
| ------ | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------- | -------- |
| UA-001 | Profile-Filtered Alerts | Only alert on changes relevant to the user's company profile                                                                    | P1       |
| UA-002 | Impact Assessment       | Each alert includes: what changed, who it affects, what action is needed, by when                                               | P1       |
| UA-003 | Regulatory Calendar     | Upcoming changes with effective dates (e.g., CPF rate changes from Jan 1, new WFL provisions)                                   | P1       |
| UA-004 | Source Attribution      | Every alert links to the official source (gazette, MOM circular, tripartite advisory)                                           | P1       |
| UA-005 | Action Items            | Convert alerts into actionable to-do items (e.g., "Update your employment contracts by [date] to include new KET requirements") | P2       |
| UA-006 | Multi-Channel Delivery  | Email digest, in-app notifications, optional WhatsApp/Telegram                                                                  | P2       |
| UA-007 | Change History          | Archive of past alerts for audit trail                                                                                          | P2       |

### 2.8 Document Generation

**Purpose**: Create company-specific, legally compliant documents on demand.

| Req ID | Requirement              | Description                                                                                            | Priority |
| ------ | ------------------------ | ------------------------------------------------------------------------------------------------------ | -------- |
| DG-001 | Context-Aware Generation | Documents auto-populate with company profile data and relevant regulatory requirements                 | P0       |
| DG-002 | Guided Generation        | Step-by-step wizard for complex documents (e.g., retrenchment package letter requires multiple inputs) | P1       |
| DG-003 | Legal Compliance Markers | Generated documents include footnotes citing regulatory basis for each clause                          | P1       |
| DG-004 | Multi-Format Export      | Export as DOCX (editable), PDF (final), or plain text                                                  | P1       |
| DG-005 | Version Control          | Track document versions. Alert when a generated document may be outdated due to regulatory changes     | P2       |
| DG-006 | Bulk Generation          | Generate documents for multiple employees (e.g., retrenchment letters for all affected employees)      | P2       |
| DG-007 | Custom Branding          | Company logo and letterhead on generated documents                                                     | P2       |
| DG-008 | Clause Library           | Modular clause library for building custom contracts and policies                                      | P2       |

---

## 3. Advisory Domains -- Complete Taxonomy

### Domain 1: Employment Contracts and Terms

| Sub-topic                                                               | Key Regulations                                          | Complexity |
| ----------------------------------------------------------------------- | -------------------------------------------------------- | ---------- |
| 1.1 Types of employment (full-time, part-time, fixed-term, casual, gig) | EA Part I, Part IV                                       | Medium     |
| 1.2 Key Employment Terms (KET) -- mandatory written terms               | EA s95-98, MOM KET requirements                          | Medium     |
| 1.3 Probation periods and confirmation                                  | Common law, best practice                                | Low        |
| 1.4 Non-compete and restraint of trade clauses                          | Common law                                               | High       |
| 1.5 Confidentiality and IP assignment                                   | Common law, Copyright Act                                | Medium     |
| 1.6 Employment Act coverage determination                               | EA s2 (definitions), Part IV coverage ($4,500 threshold) | Medium     |
| 1.7 Contract variation and amendment                                    | EA, common law                                           | Medium     |
| 1.8 Part-time employee regulations                                      | Employment Act (Part-Time Employees) Regulations         | Medium     |

### Domain 2: Wages, Salary, and Allowances

| Sub-topic                                                          | Key Regulations                        | Complexity |
| ------------------------------------------------------------------ | -------------------------------------- | ---------- |
| 2.1 Salary payment obligations (timing, mode, itemised payslip)    | EA s20-26, EA (Itemised Payslips)      | Medium     |
| 2.2 Deductions from salary (permissible vs impermissible)          | EA s27-34                              | Medium     |
| 2.3 Bonus and AWS (13th month)                                     | Common practice, collective agreements | Low        |
| 2.4 Allowances (transport, housing, meal) -- CPF and tax treatment | CPF Act, IRAS guidelines               | High       |
| 2.5 Commission and incentive structures                            | EA interaction with OT calculations    | High       |
| 2.6 Progressive Wage Model (PWM) -- sector-specific minimum wages  | Various sectoral Tripartite Clusters   | High       |
| 2.7 Local Qualifying Salary (LQS)                                  | MOM requirements for WP/S Pass quota   | Medium     |
| 2.8 Salary benchmarks by sector and role                           | MOM Occupational Wage Survey           | Low        |

### Domain 3: Working Hours, Overtime, and Rest Days

| Sub-topic                                           | Key Regulations                                      | Complexity |
| --------------------------------------------------- | ---------------------------------------------------- | ---------- |
| 3.1 Contractual hours and maximum working hours     | EA s38 (44 hours/week, 88 hours/fortnight)           | Medium     |
| 3.2 Overtime limits and calculations                | EA s38(4) (72 hours/month cap), s37 (1.5x rate)      | High       |
| 3.3 Rest day provisions and work on rest days       | EA s36, s37(3) -- different rates for whole/half day | High       |
| 3.4 Public holiday entitlements and pay             | EA s88-89 -- 11 gazetted holidays                    | Medium     |
| 3.5 Shift work arrangements                         | EA s40 -- shift worker provisions                    | Medium     |
| 3.6 Part IV applicability ($4,500 salary threshold) | EA Part IV                                           | Medium     |
| 3.7 Meal breaks and working conditions              | EA s38(2) -- break after 6 continuous hours          | Low        |
| 3.8 On-call and standby arrangements                | Common law, best practice                            | Medium     |

### Domain 4: Leave Entitlements

| Sub-topic                                                    | Key Regulations                                   | Complexity |
| ------------------------------------------------------------ | ------------------------------------------------- | ---------- |
| 4.1 Annual leave (statutory minimum, pro-rating, encashment) | EA s43-44 -- 7 days after 3 months, up to 14 days | Medium     |
| 4.2 Sick leave and hospitalization leave                     | EA s89, Medical Certificates                      | Medium     |
| 4.3 Maternity leave (16 weeks, government-paid, eligibility) | CDCSA s9-12, EA s76-80                            | High       |
| 4.4 Paternity leave (2 weeks government-paid)                | CDCSA s12A-12E                                    | Medium     |
| 4.5 Shared parental leave (upcoming expanded provisions)     | CDCSA amendments                                  | Medium     |
| 4.6 Childcare leave (6 days/year, age of child, cap)         | CDCSA s12B                                        | Medium     |
| 4.7 Extended childcare leave (2 days for child 7-12)         | CDCSA s12C                                        | Low        |
| 4.8 Adoption leave                                           | CDCSA s12AA                                       | Medium     |
| 4.9 Unpaid infant care leave                                 | CDCSA s12D                                        | Low        |
| 4.10 Compassionate/bereavement leave                         | Best practice (no statutory requirement)          | Low        |
| 4.11 Marriage leave                                          | Best practice                                     | Low        |
| 4.12 National Service (NS) leave -- reservist obligations    | Enlistment Act                                    | Medium     |
| 4.13 Leave for union activities                              | Industrial Relations Act s82                      | Low        |
| 4.14 Sabbatical and study leave                              | Best practice                                     | Low        |

### Domain 5: Central Provident Fund (CPF)

| Sub-topic                                                             | Key Regulations                                 | Complexity |
| --------------------------------------------------------------------- | ----------------------------------------------- | ---------- |
| 5.1 Contribution rates by age tier and citizenship                    | CPF Act, CPF contribution rate tables           | High       |
| 5.2 Ordinary Wage (OW) ceiling and Additional Wage (AW) ceiling       | CPF Act s7, current ceiling amounts             | High       |
| 5.3 Employer obligations (registration, payment deadlines, penalties) | CPF Act s7, s52 -- 14th of following month      | Medium     |
| 5.4 CPF on different components (basic salary, OT, bonus, allowances) | CPF Act, Schedules                              | High       |
| 5.5 Voluntary contributions                                           | CPF Act s7(4)                                   | Low        |
| 5.6 CPF for first/second-year PRs (graduated rates)                   | CPF Act, contribution rate tables               | Medium     |
| 5.7 Workfare and CPF Transition Offset schemes                        | Government schemes, eligibility criteria        | Medium     |
| 5.8 Self-employed CPF obligations                                     | CPF Act s9A (MediSave contributions)            | Medium     |
| 5.9 Penalties for late or non-payment                                 | CPF Act s52-55 -- interest charges, prosecution | High       |
| 5.10 CPF reporting and filing                                         | CPF Act s7B, electronic submission requirements | Medium     |

### Domain 6: Foreign Manpower

| Sub-topic                                                              | Key Regulations                               | Complexity |
| ---------------------------------------------------------------------- | --------------------------------------------- | ---------- |
| 6.1 Work Permit (WP) -- eligibility, quota, levy, conditions           | EFMA, Work Permit conditions                  | High       |
| 6.2 S Pass -- eligibility, quota (currently being tightened), levy     | EFMA, S Pass conditions, COMPASS-like factors | High       |
| 6.3 Employment Pass (EP) -- COMPASS framework, salary criteria         | EFMA, EP framework, COMPASS points system     | High       |
| 6.4 Personalised Employment Pass (PEP)                                 | EFMA                                          | Medium     |
| 6.5 ONE Pass                                                           | EFMA                                          | Low        |
| 6.6 Dependant's Pass and Letter of Consent (LOC)                       | EFMA                                          | Medium     |
| 6.7 Dependency Ratio Ceiling (DRC) / S Pass sub-DRC by sector          | EFMA, sector-specific ratios                  | High       |
| 6.8 Foreign worker levies by tier, sector, and qualification           | EFMA, levy schedules                          | High       |
| 6.9 Fair Consideration Framework (FCF) -- job advertising requirements | EFMA, FCF guidelines, MyCareersFuture         | High       |
| 6.10 Security bond requirements                                        | EFMA, Work Permit conditions                  | Medium     |
| 6.11 Medical insurance requirements for WP/S Pass holders              | EFMA, WP/S Pass conditions                    | Medium     |
| 6.12 Repatriation obligations                                          | EFMA s22                                      | Medium     |
| 6.13 Foreign worker housing requirements                               | EFMA, Foreign Employee Dormitories Act        | Medium     |
| 6.14 Work pass application and renewal procedures                      | EFMA, MOM procedures                          | Medium     |
| 6.15 In-principle approval (IPA) process                               | MOM procedures                                | Medium     |
| 6.16 Employer blacklisting and debarment                               | EFMA s7                                       | Medium     |
| 6.17 Change of employer procedures                                     | EFMA                                          | Medium     |

### Domain 7: Termination, Retrenchment, and Retirement

| Sub-topic                                                         | Key Regulations                                                                       | Complexity |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ---------- |
| 7.1 Termination with notice                                       | EA s10-11, contractual terms                                                          | Medium     |
| 7.2 Termination without notice (summary dismissal for misconduct) | EA s14 -- inquiry process                                                             | High       |
| 7.3 Dismissal on grounds of misconduct -- due inquiry             | EA s14 -- procedural fairness requirements                                            | High       |
| 7.4 Constructive dismissal                                        | Common law, ECT jurisdiction                                                          | High       |
| 7.5 Wrongful dismissal (Tripartite Guidelines)                    | Tripartite Guidelines on Wrongful Dismissal, EA s14(2)                                | High       |
| 7.6 Dismissal of pregnant employees                               | EA s84, CDCSA                                                                         | High       |
| 7.7 Retrenchment -- process and notifications                     | Tripartite Guidelines on Managing Excess Manpower, MOM notification (if 5+ employees) | High       |
| 7.8 Retrenchment benefits -- statutory vs market norms            | Common practice (1 month per year), collective agreements                             | Medium     |
| 7.9 Retirement age and re-employment obligations                  | Retirement and Re-employment Act -- current age 63, re-employment to 68               | High       |
| 7.10 Payment in lieu of notice                                    | EA s11                                                                                | Medium     |
| 7.11 Garden leave                                                 | Common law                                                                            | Medium     |
| 7.12 Final salary and accrued leave payments on termination       | EA s22-23                                                                             | Medium     |
| 7.13 Reference letters and post-employment obligations            | Best practice, common law                                                             | Low        |

### Domain 8: Workplace Safety and Health

| Sub-topic                                                             | Key Regulations                                              | Complexity |
| --------------------------------------------------------------------- | ------------------------------------------------------------ | ---------- |
| 8.1 Employer general duties                                           | WSHA s12                                                     | Medium     |
| 8.2 Risk assessment requirements                                      | WSH (Risk Management) Regulations                            | Medium     |
| 8.3 Incident reporting (to MOM)                                       | WSHA s44-45 -- dangerous occurrences and workplace accidents | High       |
| 8.4 Work Injury Compensation Act (WICA) claims                        | WICA -- process, timelines, compensation tables              | High       |
| 8.5 Work injury leave and medical leave entitlements                  | WICA s14-17                                                  | Medium     |
| 8.6 Workplace safety committees                                       | WSHA, WSH (General Provisions) Regulations                   | Medium     |
| 8.7 Safety training requirements                                      | WSH (Safety and Health Training) Regulations                 | Medium     |
| 8.8 Sector-specific safety requirements (construction, manufacturing) | Various WSH subsidiary legislation                           | High       |
| 8.9 Return to work programs                                           | Best practice, WICA rehabilitation                           | Medium     |
| 8.10 Occupational health screening                                    | WSH (Medical Examinations) Regulations                       | Medium     |

### Domain 9: Performance Management

| Sub-topic                                            | Key Regulations                                            | Complexity |
| ---------------------------------------------------- | ---------------------------------------------------------- | ---------- |
| 9.1 Performance appraisal frameworks                 | Best practice (no statutory requirement)                   | Medium     |
| 9.2 Performance Improvement Plans (PIP)              | Best practice, but important for termination defensibility | Medium     |
| 9.3 Probation assessment and confirmation            | Contractual, best practice                                 | Low        |
| 9.4 Documentation of poor performance                | Best practice for legal defensibility                      | Medium     |
| 9.5 Performance-linked pay and bonuses               | Contractual, common practice                               | Medium     |
| 9.6 Fair performance management (non-discriminatory) | TAFEP guidelines, upcoming WFL                             | Medium     |

### Domain 10: Grievance Handling and Dispute Resolution

| Sub-topic                                                           | Key Regulations                              | Complexity |
| ------------------------------------------------------------------- | -------------------------------------------- | ---------- |
| 10.1 Internal grievance procedures                                  | Best practice, Tripartite Advisory           | Medium     |
| 10.2 Tripartite Alliance for Dispute Management (TADM) -- mediation | Employment Claims Act, TADM procedures       | High       |
| 10.3 Employment Claims Tribunals (ECT) -- adjudication              | Employment Claims Act s12-14                 | High       |
| 10.4 MOM complaints and investigations                              | EFMA, EA enforcement provisions              | Medium     |
| 10.5 Industrial Arbitration Court (IAC)                             | Industrial Relations Act                     | High       |
| 10.6 Harassment complaints (Protection from Harassment Act)         | Protection from Harassment Act (POHA)        | Medium     |
| 10.7 Whistleblower protections                                      | Limited statutory protections, best practice | Medium     |

### Domain 11: Flexible Work Arrangements (FWA)

| Sub-topic                                               | Key Regulations                                   | Complexity |
| ------------------------------------------------------- | ------------------------------------------------- | ---------- |
| 11.1 Tripartite Guidelines on FWA (effective Dec 2024)  | Tripartite Guidelines on FWA Requests             | High       |
| 11.2 Types of FWA (flexi-time, flexi-place, flexi-load) | Tripartite Guidelines definitions                 | Medium     |
| 11.3 FWA request and response process                   | Tripartite Guidelines -- 2 months response period | Medium     |
| 11.4 Reasonable business grounds for refusal            | Tripartite Guidelines                             | Medium     |
| 11.5 FWA policy development                             | Best practice, templates                          | Medium     |
| 11.6 Technology and infrastructure for remote work      | Best practice, PDPA considerations                | Low        |

### Domain 12: Anti-Discrimination and Workplace Fairness

| Sub-topic                                                   | Key Regulations                                                            | Complexity |
| ----------------------------------------------------------- | -------------------------------------------------------------------------- | ---------- |
| 12.1 TAFEP Guidelines on Fair Employment Practices          | TAFEP guidelines -- race, religion, age, gender, disability, family status | High       |
| 12.2 Workplace Fairness Legislation (upcoming)              | Anticipated WFL provisions                                                 | High       |
| 12.3 Fair recruitment practices -- FCF and job advertising  | FCF, TAFEP, MyCareersFuture requirements                                   | Medium     |
| 12.4 Age discrimination and re-employment                   | RRA, TAFEP age-related guidelines                                          | Medium     |
| 12.5 Disability discrimination and reasonable accommodation | TAFEP guidelines, upcoming WFL                                             | Medium     |
| 12.6 Sexual harassment policies and procedures              | TAFEP advisory, POHA                                                       | Medium     |
| 12.7 Nationality-based discrimination                       | TAFEP, FCF                                                                 | Medium     |

### Domain 13: Transfer of Employees

| Sub-topic                                        | Key Regulations                           | Complexity |
| ------------------------------------------------ | ----------------------------------------- | ---------- |
| 13.1 Transfer of undertaking (business transfer) | EA s18A-18E (Singapore's TUPE equivalent) | High       |
| 13.2 Merger and acquisition employee transfers   | EA s18A-18E, common law                   | High       |
| 13.3 Secondment arrangements                     | Common law, contractual                   | Medium     |
| 13.4 Outsourcing and insourcing of functions     | EA s18A, best practice                    | Medium     |
| 13.5 Inter-company transfers within group        | Common law, CPF implications              | Medium     |

### Domain 14: Data Protection in Employment

| Sub-topic                                        | Key Regulations                                    | Complexity |
| ------------------------------------------------ | -------------------------------------------------- | ---------- |
| 14.1 Collection of employee personal data        | PDPA, Advisory Guidelines on Key Concepts          | Medium     |
| 14.2 Employee consent and deemed consent         | PDPA s13-17, employment context                    | Medium     |
| 14.3 Employee monitoring (email, internet, CCTV) | PDPA, best practice                                | Medium     |
| 14.4 Cross-border transfer of employee data      | PDPA s26, Transfer Limitation Obligation           | Medium     |
| 14.5 Data breach notification (employee data)    | PDPA s26A-26E                                      | Medium     |
| 14.6 Retention and disposal of employee records  | PDPA s25, EA record-keeping requirements (2 years) | Medium     |
| 14.7 Access requests from employees              | PDPA s21                                           | Medium     |

### Domain 15: Union and Collective Agreements

| Sub-topic                                                                 | Key Regulations                                             | Complexity |
| ------------------------------------------------------------------------- | ----------------------------------------------------------- | ---------- |
| 15.1 Trade union recognition                                              | Industrial Relations Act, Trade Unions Act                  | High       |
| 15.2 Collective bargaining process                                        | Industrial Relations Act s17-19                             | High       |
| 15.3 Collective agreement terms and enforcement                           | Industrial Relations Act s24-28                             | High       |
| 15.4 Industrial action (strikes, lockouts) -- extremely rare in Singapore | Trade Disputes Act, Criminal Law (Temporary Provisions) Act | High       |
| 15.5 Employer obligations to unionized workers                            | Industrial Relations Act                                    | Medium     |
| 15.6 NTUC and affiliated unions -- tripartite partnership                 | Understanding Singapore's tripartism                        | Low        |

### Domain 16: Payroll and Tax

| Sub-topic                                                   | Key Regulations                                                     | Complexity |
| ----------------------------------------------------------- | ------------------------------------------------------------------- | ---------- |
| 16.1 Income tax obligations (employer: IR8A, IR21)          | Income Tax Act, IRAS guidelines                                     | Medium     |
| 16.2 Tax clearance for foreign employees (IR21)             | Income Tax Act s68 -- must be done before employee leaves Singapore | High       |
| 16.3 Skills Development Levy (SDL)                          | Skills Development Levy Act -- $2-$11.25 cap                        | Low        |
| 16.4 Payroll processing requirements                        | EA (itemised payslip requirements), CPF submission                  | Medium     |
| 16.5 Benefits in kind -- tax treatment                      | IRAS guidelines on taxable/non-taxable benefits                     | Medium     |
| 16.6 Stock options and equity compensation -- tax treatment | IRAS guidelines on stock options                                    | High       |
| 16.7 Auto-Inclusion Scheme (AIS)                            | IRAS requirements for participating employers                       | Medium     |

### Domain 17: Benefits Administration

| Sub-topic                                                | Key Regulations                                                    | Complexity |
| -------------------------------------------------------- | ------------------------------------------------------------------ | ---------- |
| 17.1 Medical and dental benefits                         | Common practice, tax implications                                  | Medium     |
| 17.2 Group insurance (life, disability, hospitalization) | WP/S Pass conditions for foreign workers; best practice for locals | Medium     |
| 17.3 Flexible benefits / cafeteria plans                 | Best practice, CPF/tax implications                                | Medium     |
| 17.4 Transport and housing allowances                    | CPF treatment, tax treatment                                       | Medium     |
| 17.5 Professional development and training benefits      | Best practice, SkillsFuture                                        | Low        |
| 17.6 Employee wellness programs                          | Best practice                                                      | Low        |

### Domain 18: HR Policy Development

| Sub-topic                                         | Key Regulations                               | Complexity |
| ------------------------------------------------- | --------------------------------------------- | ---------- |
| 18.1 Mandatory policies (what must be documented) | EA (KET), PDPA (DPP), WSHA (risk assessments) | Medium     |
| 18.2 Recommended policies by company size         | Tripartite guidelines, best practice          | Medium     |
| 18.3 Policy communication and acknowledgment      | Best practice, legal enforceability           | Low        |
| 18.4 Policy review cycle                          | Best practice                                 | Low        |
| 18.5 Employee handbook structure and content      | Best practice, legal requirements             | Medium     |

---

## 4. Non-Functional Requirements

### 4.1 Accuracy Requirements

| Requirement           | Specification                                                                                                                                                           | Rationale                                                                                                            |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Legal accuracy        | Zero tolerance for incorrect statements of law. Every legal citation must be verifiable.                                                                                | Wrong legal advice exposes users to penalties, lawsuits, and fines.                                                  |
| Calculation accuracy  | 100% accuracy for CPF, levy, quota, and leave calculations against published government rates.                                                                          | Financial errors have direct monetary impact on both employer and employee.                                          |
| Guideline accuracy    | Must accurately represent tripartite guidelines, distinguishing advisory from mandatory.                                                                                | Overstating guidelines as law causes unnecessary compliance burden; understating law as guideline causes violations. |
| Temporal accuracy     | Must reflect the version of law in force at the time of query. Must not cite repealed or superseded provisions without noting the change.                               | Regulations change. Advice based on outdated law is worse than no advice.                                            |
| Confidence disclosure | When certainty is low (ambiguous provisions, novel situations, untested areas of law), must explicitly say so and recommend professional consultation.                  | Users must not be given false confidence on genuinely uncertain matters.                                             |
| Acceptable error rate | 0% for direct factual statements of law and calculations. Below 2% for contextual application of law to user scenarios (where reasonable professionals might disagree). | The platform's value depends entirely on trust.                                                                      |
| Validation mechanism  | Every factual claim must be traceable to a source document in the knowledge base. Advisory interpretations must be flagged as such.                                     | Enables audit and correction.                                                                                        |

### 4.2 Content Update Frequency

| Content Type                                    | Update Requirement                                                  | Mechanism                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------- |
| Legislative changes (Acts passed in Parliament) | Within 48 hours of gazette publication                              | Monitoring pipeline + expert review                            |
| Subsidiary legislation                          | Within 48 hours of gazette publication                              | Monitoring pipeline + expert review                            |
| MOM circulars and advisories                    | Within 24 hours of publication                                      | RSS/API monitoring + automated ingestion                       |
| CPF rate changes                                | Updated before effective date (usually announced months in advance) | Calendar-based + monitoring                                    |
| Tripartite guidelines (new or revised)          | Within 1 week of publication                                        | Monitoring + expert review (guidelines require interpretation) |
| TAFEP guidelines                                | Within 1 week of publication                                        | Monitoring + expert review                                     |
| Court/tribunal decisions of significance        | Within 2 weeks of publication                                       | Manual monitoring + expert curation                            |
| Template updates (post regulatory change)       | Within 2 weeks of underlying regulatory change                      | Triggered by knowledge base update                             |
| Calculator rate updates                         | Before effective date of rate change                                | Pre-scheduled + validation                                     |

### 4.3 Accessibility Requirements

| Requirement             | Specification                                                                                                                                             |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language                | English (primary). Plain language (no legalese unless quoting directly). Singlish-aware input parsing.                                                    |
| Reading level           | Advisory output targeted at Grade 8-10 reading level (accessible to non-specialists). Legal citations provided alongside, not instead of, plain language. |
| Device support          | Fully responsive web application. Mobile-first design (SME owners often access on phone).                                                                 |
| Accessibility standards | WCAG 2.1 AA compliance.                                                                                                                                   |
| Internet requirements   | Must work on typical Singapore broadband and mobile data connections. Latency target: response initiation within 3 seconds.                               |
| Session handling        | Conversations persist across sessions. Users can return to previous advisory threads.                                                                     |
| Onboarding              | First useful answer within 5 minutes of signup (company profile can be completed progressively).                                                          |

### 4.4 Data Privacy and Security Requirements

| Requirement                 | Specification                                                                                                                                                                           | Regulation                     |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| Company data classification | Confidential. Company profile, workforce composition, compliance status.                                                                                                                | PDPA, business confidentiality |
| Employee data               | Must NOT be required for core advisory. If employee-level data is provided (e.g., for specific calculations), it must be processed transiently and not stored without explicit consent. | PDPA                           |
| Data residency              | All data stored in Singapore. No cross-border transfer without explicit consent and PDPA-compliant safeguards.                                                                          | PDPA s26                       |
| Encryption at rest          | AES-256 for all stored data.                                                                                                                                                            | Industry standard              |
| Encryption in transit       | TLS 1.3 for all API communications.                                                                                                                                                     | Industry standard              |
| Access control              | Multi-factor authentication. Role-based access (owner, HR manager, consultant with client-level isolation).                                                                             | Security best practice         |
| Data retention              | Company profile data retained while account is active. Advisory conversation data retained for 2 years (aligned with EA record-keeping requirements). Explicit deletion capability.     | PDPA s25                       |
| Audit logging               | All advisory interactions logged (for accuracy review and continuous improvement). Logs must not contain employee PII.                                                                  | Compliance + quality assurance |
| Penetration testing         | Annual third-party penetration testing.                                                                                                                                                 | Security best practice         |
| Consultant data isolation   | For Persona D (HR consultants), strict data isolation between client profiles. Consultant cannot inadvertently access one client's data while in another client's context.              | PDPA, professional ethics      |
| AI model data usage         | User conversations must NOT be used to train AI models without explicit opt-in consent.                                                                                                 | PDPA, user trust               |
| Breach notification         | Notify affected users within 72 hours of confirmed data breach (aligns with PDPA s26D).                                                                                                 | PDPA s26D                      |

### 4.5 Disclaimer and Liability Framework

| Requirement             | Specification                                                                                                                                                                                                                |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| General disclaimer      | Platform provides information and guidance, not legal advice. Users should seek professional legal counsel for complex or high-stakes matters.                                                                               |
| Per-response disclaimer | Every advisory response includes a contextual disclaimer appropriate to the confidence level and stakes of the topic.                                                                                                        |
| Escalation triggers     | Certain topics must ALWAYS include a recommendation to seek professional advice: wrongful dismissal disputes, TADM/ECT proceedings, union negotiations, WICA claims above certain thresholds, potential criminal violations. |
| Limitation of liability | Terms of service must clearly limit liability for reliance on platform advice.                                                                                                                                               |
| Professional indemnity  | Platform operator should carry professional indemnity insurance.                                                                                                                                                             |
| Distinction enforcement | UI must visually distinguish between: (1) direct quotes of law, (2) platform's interpretation of law, (3) best practice recommendations.                                                                                     |
| Update currency notice  | Every response should indicate the currency of the regulatory data it is based on (e.g., "Based on regulations current as of [date]").                                                                                       |

### 4.6 Performance Requirements

| Metric                       | Target                                                                                        | Rationale                                                 |
| ---------------------------- | --------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Advisory response initiation | Under 3 seconds (first token / streaming start)                                               | User experience -- people expect chat-like responsiveness |
| Full advisory response       | Under 15 seconds for standard questions. Under 30 seconds for complex multi-domain questions. | Balance between speed and thoroughness                    |
| Calculator results           | Under 2 seconds                                                                               | Calculators should feel instant                           |
| Document generation          | Under 30 seconds for simple documents. Under 2 minutes for complex multi-page documents.      | Acceptable for document generation context                |
| Search results               | Under 2 seconds                                                                               | Knowledge base search should be fast                      |
| Concurrent users             | Support 500 concurrent users at launch. Scale to 5,000.                                       | Singapore SME market size; initial target segment         |
| Uptime                       | 99.5% (allows ~43 hours downtime/year). Target 99.9% within 12 months.                        | Not life-critical, but professional tool                  |
| Data backup                  | RPO: 1 hour. RTO: 4 hours.                                                                    | Business continuity                                       |

---

## 5. Compliance Threshold Map

A critical feature unique to this platform: tracking which regulations kick in at different company sizes and helping users prepare before they cross thresholds.

| Threshold                           | Obligation                                                                                                  | Regulation/Guideline                                       |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| 1+ employees                        | Employment Act coverage (for eligible employees), CPF contributions, WICA coverage                          | EA, CPF Act, WICA                                          |
| 1+ foreign workers                  | Work pass conditions, levy, quota monitoring, security bond (WP), medical insurance                         | EFMA                                                       |
| 5+ employees retrenched in 6 months | Mandatory notification to MOM                                                                               | EA s45A, Tripartite Guidelines on Managing Excess Manpower |
| 10+ employees                       | Tripartite Guidelines on FWA apply ("should comply"). Progressive Wage Model may apply (sector-specific).   | TG-FWA, PWM orders                                         |
| 25+ employees                       | Fair Consideration Framework -- must advertise on MyCareersFuture before hiring EP/S Pass (with exemptions) | FCF, EFMA                                                  |
| 25+ employees                       | Tripartite Standards on various topics become more relevant                                                 | Various TS                                                 |
| 50+ employees                       | Various tripartite guidelines reference this tier                                                           | Various TG                                                 |
| 200+ employees                      | Enhanced MOM scrutiny, more detailed reporting requirements                                                 | MOM enforcement practice                                   |
| Sector-specific                     | Construction/marine/process sectors: different DRC, levy tiers, safety requirements                         | EFMA schedules, WSHA                                       |

---

## 6. Integration Requirements

### 6.1 External Data Sources

| Source                          | Data                                               | Integration Type                  | Update Frequency |
| ------------------------------- | -------------------------------------------------- | --------------------------------- | ---------------- |
| Singapore Statutes Online (SSO) | Legislation text                                   | Web scraping / API (if available) | Weekly check     |
| MOM website                     | Circulars, advisories, pass conditions, levy rates | Web scraping / RSS                | Daily check      |
| CPF Board website               | Contribution rates, scheme details                 | Web scraping / API                | Monthly check    |
| Government Gazette              | New/amended legislation                            | API / monitoring                  | As published     |
| TAFEP website                   | Guidelines, advisories                             | Web scraping                      | Weekly check     |
| MyCareersFuture                 | FCF compliance requirements                        | API (if available)                | As needed        |
| TADM / ECT                      | Case summaries (if published)                      | Manual curation                   | Monthly          |

### 6.2 Internal System Integrations (Future)

| System                                                         | Integration                            | Priority |
| -------------------------------------------------------------- | -------------------------------------- | -------- |
| Payroll systems (common SG HRIS platforms)                      | Import employee data for calculations  | P3       |
| ACRA BizFile+                                                  | Auto-populate company profile from UEN | P2       |
| CPF e-Submit                                                   | Cross-reference submission status      | P3       |
| Calendar systems                                               | Regulatory deadline reminders          | P3       |

---

## 7. Risk Assessment

### Critical Risks (High Probability, High Impact)

**RISK-001: Incorrect Legal Advice**

- Description: Platform provides wrong interpretation of law, user acts on it, suffers penalty or loss.
- Probability: Medium (complex regulatory landscape makes errors possible).
- Impact: Critical (legal liability, user harm, platform credibility destroyed).
- Mitigation: Multi-layer validation (AI output checked against structured knowledge base), mandatory source citations, confidence scoring, escalation triggers, professional indemnity insurance.
- Prevention: Expert-curated knowledge base (not just web-scraped), regular accuracy audits, user feedback loop, clear disclaimers.

**RISK-002: Outdated Regulatory Content**

- Description: Regulations change but knowledge base is not updated, leading to advice based on superseded law.
- Probability: High (Singapore updates employment regulations frequently).
- Impact: Critical (same as RISK-001).
- Mitigation: Automated monitoring of regulatory sources, version-dated knowledge base entries, staleness alerts, update pipeline with SLA.
- Prevention: Dedicated content maintenance process, regulatory calendar tracking announced changes.

**RISK-003: Context Misapplication**

- Description: Platform applies correct law to wrong context (e.g., advises on EA Part IV provisions for an employee earning above the threshold).
- Probability: Medium (contextual rules are complex -- sector, size, salary, citizenship all interact).
- Impact: High (advice is technically correct law but wrong for the user's situation).
- Mitigation: Company profile validation, explicit applicability checks before every advisory, "Does this apply to me?" verification layer.
- Prevention: Robust context engine with applicability rules mapped to every provision.

### High Risks (Monitor Closely)

**RISK-004: Over-Reliance by Users**

- Description: Users treat platform as authoritative legal counsel and do not seek professional advice on complex matters.
- Probability: High (the platform is designed to be comprehensive -- users may not see the limits).
- Impact: High (user harm on complex matters).
- Mitigation: Clear escalation triggers, mandatory disclaimers on high-stakes topics, confidence indicators, "seek professional advice" recommendations baked into responses on complex topics.

**RISK-005: Data Breach of Company HR Data**

- Description: Sensitive company and workforce data exposed through security breach.
- Probability: Low-Medium (standard SaaS risk).
- Impact: High (PDPA violations, loss of trust, business confidentiality breach).
- Mitigation: Encryption, access controls, regular penetration testing, PDPA-compliant data handling.
- Prevention: Security-first architecture, minimal data collection, data isolation.

**RISK-006: AI Hallucination**

- Description: AI model generates plausible but fabricated legal provisions, case references, or regulatory requirements.
- Probability: Medium (inherent LLM risk).
- Impact: Critical (fabricated law cited as real -- worse than no advice).
- Mitigation: RAG architecture grounding all responses in verified knowledge base, citation validation (every cited provision must exist in KB), hallucination detection layer.
- Prevention: Constrained generation (only allow claims supported by KB), never generate without retrieval grounding.

### Medium Risks (Plan For)

**RISK-007: Scalability of Content Maintenance**

- Description: As regulatory corpus grows, maintaining accuracy and currency becomes unsustainable.
- Probability: Medium (Singapore adds regulations regularly).
- Impact: Medium (degraded quality over time).
- Mitigation: Structured content management system, automated change detection, expert review workflows.

**RISK-008: User Trust Calibration**

- Description: Users either over-trust or under-trust the platform, leading to harm or non-adoption.
- Probability: Medium.
- Impact: Medium.
- Mitigation: Transparent confidence indicators, accuracy track record, user education.

### Low Risks (Accept)

**RISK-009: Regulatory Ambiguity**

- Description: Some areas of law are genuinely ambiguous or untested. Platform may present one interpretation when others are valid.
- Probability: Low-Medium (most employment law is well-established).
- Impact: Medium.
- Mitigation: Flag ambiguous areas explicitly, present multiple interpretations where they exist.

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-6)

**Objective**: Core advisory engine with knowledge base for 3 highest-demand domains.

- Company profile setup (basic: sector, headcount, worker mix)
- Knowledge base: Employment Act, CPF, Foreign Manpower (the three domains every SME needs)
- Advisory engine: Natural language Q&A with source citations
- CPF calculator, foreign worker levy calculator, quota calculator
- Basic employment contract template
- Disclaimer framework

**Success Criteria**: A user can sign up, set up their company profile, and get accurate answers about EA, CPF, and foreign worker obligations.

### Phase 2: Core Advisory (Weeks 7-12)

**Objective**: Expand to all critical domains, add compliance checking and document generation.

- Knowledge base: All remaining domains (leave, termination, WSH, FWA, anti-discrimination, etc.)
- Template library: Employment contracts (all types), key letters, essential policies
- Compliance checker: Basic "is my practice compliant?" assessments
- Leave entitlement calculator, overtime calculator, notice period calculator
- Multi-turn conversation support
- Confidence indicators and escalation triggers
- Distinction markers (law vs guideline vs best practice)

**Success Criteria**: All 18 advisory domains covered. Users can generate core documents and check compliance.

### Phase 3: Full Platform (Weeks 13-18)

**Objective**: Complete feature set, polish, and enterprise readiness.

- Full template library with guided generation
- Compliance audit (comprehensive cross-domain assessment)
- Update alerts (profile-filtered regulatory change notifications)
- Threshold tracker
- Scenario modeling tools
- Consultant mode (multi-client profiles)
- Document version control
- Employee handbook generator
- Regulatory calendar
- Advanced calculators (cost-to-company, retrenchment benefits, salary benchmarks)

**Success Criteria**: All feature categories functional. All four personas can complete their top 10 tasks.

### Phase 4: Scale and Optimize (Weeks 19-24)

**Objective**: Performance, accuracy validation, and market readiness.

- Accuracy audit (expert review of advisory outputs across all domains)
- Performance optimization
- User testing with real SME owners
- Content gap identification and filling
- Bilingual support (English + Mandarin)
- Integration API foundations
- Security audit and penetration testing
- Production deployment and monitoring

**Success Criteria**: Accuracy audit passes (0% factual errors, under 2% interpretation variance). Performance targets met. User testing validates persona journeys.

---

## 9. Success Criteria Summary

| Criterion           | Metric                                             | Target                                              |
| ------------------- | -------------------------------------------------- | --------------------------------------------------- |
| Accuracy            | Expert audit of 500 random advisory outputs        | 0% factual errors, under 2% interpretation variance |
| Coverage            | % of top-10 persona questions answerable           | 100% for all four personas                          |
| Speed               | Time to first useful answer after signup           | Under 5 minutes                                     |
| User satisfaction   | Post-session rating                                | 4.5/5 or higher                                     |
| Calculator accuracy | Validation against government-published rates      | 100% match                                          |
| Template compliance | Expert review of all templates against current law | 100% compliant                                      |
| Content currency    | Average age of regulatory content                  | Under 7 days from source update                     |
| Uptime              | Monthly availability                               | 99.5% or higher                                     |
| Response time       | Advisory response start (P95)                      | Under 3 seconds                                     |
| Trust               | Users who rate advice as "trustworthy"             | Over 90%                                            |
