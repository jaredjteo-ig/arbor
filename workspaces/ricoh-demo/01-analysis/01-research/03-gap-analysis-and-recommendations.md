# Gap Analysis & Recommendations

**Date**: 2026-03-24

---

## Gap Assessment: Demo Blockers vs. Nice-to-Haves

### Blockers (Must Fix Before Demo)

| #   | Gap                                          | Impact                                                  | Effort                                         |
| --- | -------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------- |
| B1  | Old branding in screenshots/some UI elements | Screenshots show "AITE" not "Arbor" — confusing in demo | Low — redeploy with latest code                |
| B2  | No demo seed data for HRIS modules           | Empty tables for payroll, employees, leave look dead    | Medium — seed realistic demo company           |
| B3  | Conversations lost on server restart         | In-memory storage means demo prep work disappears       | Medium — DB persistence or pre-warm            |
| B4  | No Thai language support                     | Ricoh Thailand audience may expect Thai UI              | Low-Medium — i18n keys exist, need translation |

### High Value (Should Do If Time Allows)

| #   | Gap                                   | Impact                                                         | Effort |
| --- | ------------------------------------- | -------------------------------------------------------------- | ------ |
| H1  | Create a "Thailand preview" KB module | Even 10-20 Thai labour law provisions would prove adaptability | Medium |
| H2  | Employee search picker                | Currently requires raw IDs                                     | Medium |
| H3  | Date picker components                | Plain text dates feel unpolished                               | Medium |
| H4  | Charts in reports module              | Tables-only looks basic                                        | Medium |
| H5  | Demo walkthrough mode                 | Guided tour of features for first-time viewers                 | High   |

### Nice-to-Have (Polish)

| #   | Gap                                      | Impact                                             | Effort    |
| --- | ---------------------------------------- | -------------------------------------------------- | --------- |
| N1  | Mobile app demo-ready                    | Flutter app exists but may not be production-ready | High      |
| N2  | MCP integrations with real Thai services | Would show integration capability                  | Very High |
| N3  | Multi-language advisory responses        | Thai responses from advisory engine                | Medium    |

---

## Recommended Priority Actions

### Priority 1: Demo Data Seeding (2-3 hours)

Create a realistic demo company with:

- 25-50 employees with varied profiles (different nationalities, roles, salaries)
- 3 months of payroll history
- Leave balances and some approved/pending leave
- A few claims in various states
- Attendance records with some overtime
- Active recruitment pipeline

This turns every module from "empty table" to "working system."

### Priority 2: Verify Production Deployment (1 hour)

- Confirm the latest code (with Arbor branding) is deployed
- Verify all key demo flows work end-to-end on production
- Create a dedicated demo account with pre-seeded data
- Test the advisory engine with 5-10 prepared questions

### Priority 3: Prepare Demo Narrative (2 hours)

- Script the 5 key demo questions for the advisory engine
- Prepare the "Thailand story" slides/talking points
- Create an architecture diagram showing the pluggable jurisdiction model
- Prepare before/after comparison (ChatGPT vs Arbor on the same question)

### Priority 4 (If Time): Thailand KB Proof-of-Concept (4-6 hours)

Even a small Thai labour law module would be powerful:

- Labour Protection Act B.E. 2541 — key provisions (severance, working hours, leave)
- Social Security Act — contribution rates
- Personal income tax — withholding brackets
- A single Thai specialist agent that can answer basic questions

This turns the demo from "imagine this for Thailand" to "look, we already started."

---

## Thailand Adaptation: Full Scope Estimate

### Regulatory Domains (Equivalent to Singapore's 6)

1. **Labour Protection Act B.E. 2541** (≈ Employment Act)
2. **Social Security Act B.E. 2533** (≈ CPF Act)
3. **Revenue Code** — personal income tax (≈ IRAS)
4. **Foreign Employment Act** (≈ EFMA)
5. **Labour Relations Act B.E. 2518** (unions, collective bargaining)
6. **Occupational Safety, Health, and Environment Act** (≈ WSH Act)

### Calculators Needed

1. Social Security Fund contributions (employer 5% + employee 5%, capped at THB 750/month each)
2. Personal income tax withholding (progressive brackets)
3. Severance pay calculator (30 days - 400 days based on service length)
4. Leave entitlement calculator (6 days annual minimum + sick leave + personal leave)
5. Overtime calculator (1.5x normal, 3x on holidays)

### Architecture Advantage

The Arbor architecture is already jurisdiction-agnostic at the HRIS layer. Payroll, leave, claims, attendance, shifts — these are universal concepts. The jurisdiction-specific parts are:

- KB content (~6,500 lines to replace/adapt)
- Specialist agents (~2,800 lines to replace/adapt)
- Calculators (~2,000 lines to replace)
- Statutory filing formats (CPF e-Submit → SSO filing)

**Estimated effort for a functional Thailand version**: 2-4 weeks with the existing architecture.

---

## Competitive Landscape (Thailand HR Tech)

### Current Players

- **Workday** — Enterprise, expensive, multi-country but not deep on Thai law
- **SAP SuccessFactors** — Enterprise, Ricoh may already use this globally
- **ByteHR** — Thai-focused SaaS HR, popular with SMEs
- **Reeracoen** / **JobsDB** — Recruitment-focused, not full HRIS
- **Tiger HR** — Thai payroll provider
- **Humanica** — Thai HR SaaS, IPO'd on SET

### Arbor's Differentiation

None of these have an AI advisory engine that:

1. Grounds answers in actual legal provisions with citations
2. Has a 13-step safety chain for AI-generated legal advice
3. Provides trust lineage (EATP) for auditable AI reasoning
4. Includes a shadow agent that proactively surfaces compliance issues
5. Is offered as a free platform with AI intelligence as the premium layer

The closest comparison would be asking ChatGPT about Thai labour law — which gives unreliable, uncited, potentially dangerous advice.
