# Product Plan: HR AI Advisory Platform

## Vision

An AI-powered HR advisory platform that gives every Singapore SME owner access to the same caliber of HR guidance that large corporations get from top-tier consultants, government specialists, and legal experts — at a fraction of the cost, available 24/7, in plain language.

## Product Name

Working title: **Arbor** (AI Trusted Expert)

---

## What We're Building

A platform with two core capabilities:

### 1. Advisory Engine

An AI-powered conversational interface where SME owners ask HR questions in plain language and get accurate, contextual, cited answers. The engine knows the user's sector, company size, headcount breakdown, and foreign worker mix — so every answer is tailored.

**Examples**:

- "Can I reimburse unused sick leave as cash?" → Nuanced answer citing EA provisions, contractual considerations, and tax implications
- "I'm hiring my 6th foreign worker — what are my quota implications?" → Calculation based on actual sector, current headcount, and worker types
- "An employee wants to work from home 2 days a week" → Guidance based on TG-FWAR, with template for FWA policy

### 2. Operational Toolkit

Templates, calculators, process guides, and document generators that turn advisory into action:

- Employment contract generator (EA-compliant, sector-appropriate)
- CPF contribution calculator (all age bands, PR years, OW/AW ceilings)
- Foreign worker quota/levy calculator
- Leave entitlement calculator
- HR policy templates (leave policy, FWA policy, grievance procedure, etc.)
- Process checklists (hiring, onboarding, termination, retrenchment)
- Claims forms, timesheets, performance review templates

---

## Who It's For

### Primary: SME Owners (5-200 employees)

No HR background. Making HR decisions alongside running their business. Currently Googling, guessing, or paying consultants $300+/hour for routine questions.

### Secondary: Solo HR Managers in SMEs

Know the basics but need specialist-level backup on complex matters. Need to produce professional documents quickly.

### Tertiary: HR Consultants/Practitioners

Use as a productivity tool and reference system. Serve more clients, faster.

---

## Architecture Overview

### Knowledge Layer (Source of Truth)

- Structured, versioned regulatory knowledge base — not a simple vector store
- Every provision has: source citation, effective date, authority level (statutory / tripartite guideline / best practice), applicability rules
- Graph structure linking related provisions across domains
- Temporal versioning: knows what was in effect at any point in time

### AI Layer (Understanding + Generation)

- Hybrid RAG: queries retrieve from structured KB, filtered by company profile
- LLM generates contextual, plain-language responses grounded in retrieved provisions
- Validation layer: anti-hallucination checks, applicability verification, confidence scoring
- Calculator tools are deterministic (CPF, levy, quota math is never AI-generated)

### Context Layer (Personalization)

- Company profile: sector, headcount, worker breakdown (local/PR/EP/SP/WP), salary ranges
- Progressive completion: starts with basics, deepens over time
- Every query is filtered through the company profile

### Transparency Layer (Trust)

- Source citations on every answer (Act, section, guideline name)
- Authority level markers: [STATUTORY] / [TRIPARTITE GUIDELINE] / [BEST PRACTICE]
- Confidence indicators
- Risk-tiered disclaimers (not blanket disclaimers)
- Clear escalation to human professionals for high-stakes matters

---

## Technical Stack

| Component       | Technology                          | Rationale                                                            |
| --------------- | ----------------------------------- | -------------------------------------------------------------------- |
| Backend         | Kailash Core SDK + DataFlow + Nexus | Multi-agent orchestration, structured data, multi-channel deployment |
| AI Agents       | Kailash Kaizen                      | Specialized agents per HR domain, multi-agent coordination           |
| Knowledge Base  | PostgreSQL + pgvector               | Structured regulatory data with semantic search capability           |
| Web Frontend    | React                               | Responsive web app                                                   |
| Mobile Frontend | Flutter                             | Cross-platform mobile (iOS + Android)                                |
| API             | Nexus (API + MCP)                   | Multi-channel access                                                 |

---

## Delivery Phases

### Phase 1: Foundation (Weeks 1-6)

**Goal**: Core infrastructure + employee classification engine

- Regulatory knowledge base schema with temporal versioning
- Employee classification engine (salary, role, pass type, citizenship, sector)
- Company profile onboarding flow
- Core EA provisions populated (leave, salary, termination basics)
- CPF rate tables (all age bands, PR years)
- Basic conversational interface (web)

**Users can**: Set up their company profile, ask basic EA and CPF questions, get cited answers.

### Phase 2: Advisory Core (Weeks 7-14)

**Goal**: Full advisory engine for the most common HR questions

- CPF contribution calculator (all scenarios including OW/AW ceiling)
- Leave entitlement calculator (all statutory leave types)
- Foreign worker quota/levy calculator (all sectors)
- Termination process advisor (notice periods, entitlements, wrongful dismissal guidance)
- COMPASS scoring model for EP applications
- Fair employment practices advisory (TAFEP compliance)
- FWA request handling guidance (TG-FWAR)

**Users can**: Get accurate answers to the top 80% of HR questions SME owners ask.

### Phase 3: Operational Toolkit (Weeks 15-20)

**Goal**: Templates, forms, document generation

- Employment contract generator (customizable, EA-compliant)
- HR policy templates (leave, FWA, grievance, code of conduct)
- Process checklists (hiring, onboarding, offboarding, retrenchment)
- Claims forms, timesheet templates, performance review templates
- Employee handbook generator
- Compliance health check ("scan my setup for gaps")

**Users can**: Generate compliant documents tailored to their company, run a compliance audit.

### Phase 4: Full Platform (Weeks 21-28)

**Goal**: Mobile app, regulatory updates, advanced features

- Flutter mobile app
- Regulatory change monitoring and user notifications
- Sector-specific playbooks (F&B, construction, tech, services, manufacturing)
- Cross-domain advisory (e.g., "retrenchment" surfaces CPF, tax, work pass, and notification obligations simultaneously)
- Workplace safety and health advisory
- PDPA compliance for HR
- Growth-stage triggers ("You just hit 25 employees — here's what changes")

**Users can**: Access the full advisory and toolkit on any device, stay current with regulatory changes.

### Phase 5: Scale (Weeks 29+)

**Goal**: Ecosystem and advanced capabilities

- HRIS integrations (third-party platform APIs)
- Advanced document generation (complex employment contracts, collective agreements guidance)
- Multi-language support (Chinese, Malay, Tamil) if demand warrants
- Analytics dashboard (workforce composition, compliance status, cost modeling)
- PSG listing process
- API for third-party integration

---

## Disclaimer & Liability Framework

### Philosophy: Transparent, Not Excessive

Human consultants make mistakes. Human lawyers give wrong advice. The standard is not perfection — it is transparency, reasonable care, and clear escalation.

### Three-Tier Approach

**Platform Level** (Terms of Service):

- Platform provides HR information and guidance, not legal advice
- Based on publicly available Singapore regulations as understood at time of response
- Users should verify critical decisions with qualified professionals
- Professional indemnity insurance in place

**In-Conversation** (Risk-Tiered):

- **Green** (factual lookups: CPF rates, leave entitlements): Answer directly with source citation. No per-query disclaimer.
- **Amber** (guidance: policy design, best practices): Light framing — "Based on current tripartite guidelines..."
- **Red** (high-stakes: termination disputes, discrimination claims, TADM proceedings): Strong disclosure + recommendation to consult a professional + offer to connect with one.

**Error Correction**:

- When wrong advice is identified: notify affected users, correct the knowledge base, document the correction
- Transparent error log (if a regulation changed and our update lagged, say so)

### CARE Framework Integration

- Human-on-the-Loop governance: human experts validate knowledge base updates, not the AI
- Trust lineage via EATP: every piece of advice traceable from user query → retrieved provisions → generated response
- Constraint envelopes: hard boundaries on what the AI can and cannot advise on

---

## Success Metrics

| Metric                      | Target                           | How Measured                            |
| --------------------------- | -------------------------------- | --------------------------------------- |
| Advisory accuracy (factual) | >99% on statutory facts          | Expert audit of random sample (monthly) |
| User satisfaction           | >4.2/5.0                         | Post-interaction rating                 |
| Knowledge currency          | <48 hours lag on gazette changes | Monitoring dashboard                    |
| Engagement                  | >3 queries per user per month    | Analytics                               |
| Conversion (free to paid)   | >5%                              | Revenue analytics                       |
| Churn                       | <5% monthly                      | Subscription analytics                  |

---

## Open Questions for User Decision

1. **Platform name** — "Arbor" is a working title. What do you want to call it?
2. **Language** — English only at launch, or multi-language from the start?
3. **Pricing** — Freemium with paid tiers? Flat rate? Per company size?
4. **Geographic scope** — Singapore only initially, or architect for regional expansion?
5. **Human escalation** — Should the platform offer "connect to a real HR consultant" for complex cases? If yes, in-house or partner network?
6. **PSG listing** — Should we prioritize PSG pre-approval in the launch plan?
