# Milestone 2: Knowledge Base & Agent Team

**What users can do after this milestone**: Set up their company profile, ask HR questions in plain English (including Singlish), and get accurate, cited answers from a team of specialized AI agents. Basic templates (employment contract, KET, leave policy) available for download. CPF calculator works. Search the knowledge base.

**Tasks**: 16

---

## T014: Knowledge base content pipeline and tooling

Define and build the process for populating the KB (before populating it):

- Content extraction tooling: scripts to parse regulatory source documents into structured provision format
- LLM-assisted extraction with mandatory human review: AI drafts plain_summary, interpretation_notes, and practical_examples; domain expert validates
- Quality checklist per provision: formal_text verified against source, plain_summary accuracy-checked, applicability_rules tested with examples, cross_references validated, effective_date confirmed
- Import pipeline: bulk import script for provisions with validation (rejects incomplete records)
- Admin scripts for KB management: add provision, update provision (creates new version, soft-deletes old), add rate table, query provision status
- Embedding generation pipeline: batch generate pgvector embeddings for all provisions
- Validation suite: automated checks that every provision has required fields, every cross-reference target exists, every rate table has a source_url

**Red team fix R2-G03**: The KB population process (not just the content) is the single largest schedule risk and needs dedicated tooling.
**Red team fix C3**: KB pipeline tooling reduces the per-provision effort from hours to minutes.

---

## T015: Knowledge base population — Employment Act (priority domain 1)

Populate the structured KB with all EA provisions:

- Part IV: hours of work, overtime, rest days (applicability rules: workmen any salary, non-workmen ≤$2,600)
- Part X: annual leave entitlements by year of service
- Sick leave (Section 89): 14 outpatient + 60 hospitalization days
- Termination and dismissal: notice periods, summary dismissal (Section 14), wrongful dismissal
- Salary: payment timelines, deduction limits, itemized payslips, KET requirements
- Maternity protection (cross-reference to CDCSA)
- Employment records retention requirements

Each provision gets: formal_text, plain_summary, interpretation_notes, effective_date, authority_level, applicability_rules, cross_references, practical_examples.
Generate pgvector embeddings for semantic search.
Validate using T014 pipeline and quality checklist.

---

## T016: Knowledge base population — CPF (priority domain 2)

Populate all CPF provisions:

- Contribution rate tables for ALL age bands (≤55, 55-60, 60-65, 65-70, >70)
- Separate rates for: Singapore Citizens, PR 1st year, PR 2nd year, PR 3rd year+
- OW ceiling ($6,800/month), AW ceiling ($102,000 - total OW)
- Allocation rates to OA, SA, MA by age band
- Platform worker CPF (phased introduction)
- Late payment penalties (18% p.a. interest)
- Voluntary contributions

All rate tables with effective dates for temporal queries ("What was the CPF rate in 2024?").
Temporal query resolution: historical rate lookup by date, clear labeling of historical vs. current information.

**Red team fix S4**: PR year explicitly modeled in all CPF rate tables.
**Red team fix R2-GAP2**: Rate tables support temporal queries with version history.

---

## T017: Knowledge base population — Foreign Manpower (priority domain 3)

Populate all foreign manpower provisions:

- DRC/quota ratios by sector (construction, manufacturing, marine, process, services)
- S Pass and WP sub-quotas per sector
- Levy tiers and rates by sector, worker type, tier position
- COMPASS framework: all criteria, scoring, sector benchmarks
- EP/S Pass/WP salary thresholds (including higher thresholds for financial services and older workers)
- Fair Consideration Framework: MyCareersFuture requirements, exemptions
- Work pass conditions and employer obligations (housing, medical, upkeep for WP holders)
- Pass cancellation and transfer rules

---

## T018: Knowledge base population — TAFEP & Workplace Fairness (priority domain 4)

Populate fair employment and anti-discrimination provisions:

- Tripartite Guidelines on Fair Employment Practices (TGFEP): all stages from recruitment to termination
- Tripartite Guidelines on FWA Requests (TG-FWAR): process requirements, response timelines, reasonable business grounds, appeal mechanism
- Tripartite Guidelines on Wrongful Dismissal
- Tripartite Advisory on Managing Excess Manpower
- All Tripartite Standards (grievance handling, recruitment practices, work-life harmony, etc.)

**Red team fix C1**: Workplace Fairness Legislation (expected 2026-2027) — include all available details, flag as upcoming, ensure agents can advise on preparation.

---

## T019: Knowledge base population — Tax, WSH, and remaining domains

Populate remaining regulatory domains:

- IRAS: employment income tax treatment, BIK, IR8A/IR8S filing, tax clearance (IR21), stock options
- WSHA: employer duties, sector-specific requirements, incident reporting, bizSAFE, penalties
- Retirement and Re-employment Act: retirement age (63→64 from Jul 2026), re-employment age (68→69), Employment Assistance Payment
- CDCSA: all leave types (maternity, paternity, shared parental, childcare, infant care, adoption)
- WICA: employer liability, compulsory insurance, compensation framework
- Industrial Relations Act: union recognition, collective bargaining basics
- PDPA: employee data obligations, consent, breach notification
- Platform Workers Act: CPF and work injury provisions

---

## T020: Core SDK — CPF contribution calculator workflow

Build deterministic CPF calculation workflow:

- Input: citizenship_status, pr_year, age_band, monthly_ow, monthly_aw (optional)
- Nodes: rate table lookup (DataFlow), OW ceiling check ($6,800), AW ceiling check ($102,000 - total OW), contribution calculation, allocation to OA/SA/MA
- Output: employer_contribution, employee_contribution, total, breakdown by OW/AW, allocation by account
- Handle all edge cases: OW exceeding ceiling, AW exceeding ceiling, PR graduated rates
- Temporal support: accept optional effective_date parameter for historical rate lookups
- Comprehensive test suite against CPF Board published examples

---

## T021: Core SDK — foreign worker quota/levy calculator workflow

Build deterministic quota and levy calculation workflow:

- Input: sector, headcount_local, headcount_pr, headcount_ep, headcount_sp, headcount_wp, scenario (hire type + count)
- Nodes: sector DRC lookup, current ratio calculation, projected ratio calculation, sub-quota checks, levy tier determination, levy cost calculation
- Output: current_ratio, projected_ratio, within_limit (boolean), levy_per_worker, total_monthly_levy, warnings (approaching ceiling, etc.)
- Support what-if scenarios (multiple hire scenarios in one call)

---

## T022: Core SDK — leave entitlement calculator workflow

Build deterministic leave calculation workflow:

- Input: years_of_service, employment_type (FT/PT), leave_type, citizenship (for government-paid leave eligibility), number_of_children, child_ages, child_citizenship
- Output: days_entitled, calculation_basis, who_pays (employer vs government), government_claim_cap
- Handle all leave types: annual, sick, maternity (16 weeks), paternity (2 weeks), shared parental, childcare, infant care, adoption
- Pro-ration for part-time and partial years

---

## T023: Agent team integration testing

Test the full agent coordination pipeline end-to-end:

- Single-domain queries route correctly (e.g., leave question → EmploymentActAgent)
- Cross-domain queries engage parallel specialists (e.g., retrenchment → EA + ForeignManpower + CPF + TAFEP)
- Calculator queries dispatch to deterministic workflows (e.g., CPF rate question → CPFAgent + CalculatorAgent)
- SharedMemoryPool coordination: all specialist outputs tagged correctly
- ComplianceAgent reads cross-domain outputs and flags issues
- ResponseSynthesizer produces coherent answers with citations
- Risk-tier classification works (GREEN/AMBER/RED)
- Trust lineage recorded for every advisory response
- **Multi-turn context**: 10+ turn conversations maintain context correctly
- **Singlish queries**: test with natural Singapore English input ("My staff resign already, need pay notice period or not?")
- **Basic load test**: 10 concurrent advisory sessions to catch architectural bottlenecks early

Test with the top 10 questions from each persona in the requirements analysis.

**Red team fix M2**: Singlish validation starts here, not deferred to M3.
**Red team fix R2-R05**: Basic concurrency test catches bottlenecks early.

---

## T024: Onboarding flow (React web)

Build the 4-screen onboarding flow:

- O1: Welcome screen with sign-up (connects to T012 auth)
- O2: Company profile setup (multi-step: sector → headcount → workforce breakdown → salary range). Progressive — steps 2-3 skippable. "Why do we ask this?" collapsible on each step.
- O3: Instant compliance snapshot (3-5 insights with risk-tier badges, compliance gauge)
- O4: First question prompt with sector-contextual suggested questions + voice input

Company profile saves to DataFlow Company model via Nexus API.
Compliance snapshot calls the agent team for a quick assessment.

---

## T025: Onboarding flow (Flutter mobile)

Build matching onboarding flow for Flutter:

- Same 4 screens adapted for mobile (full-screen per step, swipe navigation)
- Voice input prominent on first question screen
- Disable autocorrect on chat input (Singlish support)

**Red team fix M2**: Test with actual Singlish HR queries during QA. Ensure LLM handles code-switching.

---

## T026: Advisory chat interface (React web)

Build the core advisory chat interface:

- ChatContainer with conversation area (80% of screen) + context bar (collapsible, shows company profile)
- Message bubbles: user (right-aligned, primary-light background) and system (left-aligned, full-width, white)
- System responses include: risk-tier badge, plain-language answer, company-specific application, source citations (clickable), related template downloads, follow-up suggestions
- RED responses: red left border, warning icon, immediate obligations section, "connect to specialist" CTA
- FeedbackButtons component on every system response (thumbs up/down + "What was wrong?" text field)
- Chat input bar: text input + microphone button + send button
- Suggested follow-up prompts as tappable chips
- Streaming response (SSE) — answer appears word-by-word via T009 SSE endpoint
- Conversation history sidebar (grouped by Today/This Week/This Month) with search

---

## T027: Advisory chat interface (Flutter mobile)

Build matching chat interface for Flutter:

- Same conversation structure adapted for mobile
- FeedbackButtons on every system response
- Voice input with speech-to-text (Singapore English accent support)
- Bottom input bar with keyboard management
- Suggested prompts scroll horizontally
- Pull-to-refresh on conversation history
- Haptic feedback on send

---

## T028: Essential templates — Phase 1 bundle

Create 10-15 essential document templates available from day one:

- Employment Contract (full-time, EA-compliant with all KET)
- Employment Contract (part-time, with pro-rated provisions)
- Key Employment Terms document (standalone KET)
- Annual Leave Policy
- Sick Leave Policy
- Termination Letter (with notice)
- Resignation Acceptance Letter
- Warning Letter (1st, 2nd, final)
- FWA Request Form
- FWA Policy template
- Expense Claims Form
- Timesheet Template

Each template linked to relevant KB provisions with compliance notes.
Available as downloadable DOCX/PDF from the advisory chat and template library.

**Red team fix S2**: These are available from Milestone 2, not deferred to Phase 3.
