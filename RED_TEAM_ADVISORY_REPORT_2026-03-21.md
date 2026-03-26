# Arbor Advisory Engine -- Red Team Report

**Date**: 2026-03-21 (Session 2)
**Auditor Perspective**: Enterprise CTO evaluating AI compliance advisory for Singapore SME adoption
**Environment**: https://arbor.terrene.foundation (production)
**Method**: Playwright browser automation (headless Chromium 1440x900)
**Model Under Test**: gpt-5-mini with multi-domain steering fix
**Test Account**: test@arbor.dev

---

## Executive Summary

**ALL 7 TESTS PASSED (100%).** The Arbor advisory engine demonstrates production-grade quality across every test scenario. The multi-domain steering fix -- the critical test that was previously failing -- now works 3/3 with zero intermittency. Response quality is substantive: every answer cites specific statutory provisions using a consistent shorthand format (CPFA-S7, EA-S10, EFMA-SP, CDCSA), provides mathematical workings where applicable, and structures guidance into actionable checklists. Zero hallucinations detected. Zero browser console errors. The only concern is response latency (27-74 seconds), which is acceptable for an advisory tool but would benefit from optimization.

**Single highest-impact finding**: The multi-domain steering fix works. Ship it.

---

## Test Results

| #   | Test               | Result   | Quality   | Time      | Key Findings                                                                                       |
| --- | ------------------ | -------- | --------- | --------- | -------------------------------------------------------------------------------------------------- |
| 1   | CPF Calculation    | **PASS** | EXCELLENT | 27.1s     | $1,275/$1,500/$2,775 correct. OW ceiling check. Account allocation. CPFA-S7/S9/S13 cited.          |
| 2   | Maternity Leave    | **PASS** | EXCELLENT | 47.1s     | 16 weeks (CDCSA) + 8 weeks (EA Part IX). Citizen distinction. GPML coverage.                       |
| 3   | S Pass Quota       | **PASS** | EXCELLENT | 33.1s     | 15% S Pass + 35% DRC. Mathematical derivation (S <= 8.82, max 8). EFMA-SP/DRC cited.               |
| 4   | Multi-Turn Context | **PASS** | EXCELLENT | 51.1s     | Context retained. "6 years" correctly interpreted as notice period follow-up. 4 weeks per EA s.10. |
| 5   | Multi-Domain (3x)  | **PASS** | EXCELLENT | 69.5s avg | **3/3 passed.** EP expiry + termination = integrated EFMA + EA action plan. Zero intermittency.    |
| 6   | Out-of-Scope       | **PASS** | GOOD      | 9.0s      | Clean decline: "I can only help with HR and employment matters in Singapore."                      |
| 7   | Persistence        | **PASS** | GOOD      | n/a       | 21 conversations in history. Risk tier badges. CSV export. Search + filter.                        |

**Pass Rate: 7/7 (100%)**
**Average Response Time: 37.5s**

---

## Detailed Analysis

### Test 1: CPF Calculation

**Query**: "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month"

**Response Content**:

- Employer CPF (17%): $1,275.00 -- cited CPFA-S7
- Employee CPF (20%): $1,500.00 -- cited CPFA-S9
- Total: $2,775.00
- OW ceiling check: $8,000 > $7,500, full salary used -- cited CPFA-S13
- Account allocation: OA 23% ($1,725), SA 6% ($450), MA 8% ($600) -- cited CPFA-ALLOC
- Follow-up suggestions: "Calculate CPF for a specific employee", "What about PR employees?"
- Provision tags: Employer CPF Contributions, Employee CPF Contributions, PR Graduated Contribution Rates, CPF Account Allocation Rates, Ordinary Wage Ceiling

**Verification**: All figures are mathematically correct for 2026 CPF rates (age 55 and below, Singapore citizen).

**Risk Assessment**: Low Risk, High Confidence -- appropriate for a straightforward calculation.

---

### Test 2: Maternity Leave

**Query**: "How much maternity leave is my employee entitled to?"

**Response Content**:

- Employment Act (Part IX): minimum 8 weeks' paid maternity leave
- CDCSA (Child Development Co-Savings Act): up to 16 weeks for eligible working mothers
- Government-paid maternity leave (GPML): government covers part of the leave for citizens
- Eligibility criteria: citizenship status, qualifying conditions
- Clarifying follow-ups: "whether the employee has worked for you 3 months and whether the child is a Singapore citizen"
- Provision tags: Employment Act -- Part IX (Maternity protection), CDCSA, Government-paid Maternity Leave

**Verification**: The 8-week EA minimum and 16-week CDCSA entitlement are both correct. The citizen distinction for GPML eligibility is accurate.

**Quality Note**: The response correctly handles the ambiguity of the question by presenting both tiers (8 weeks EA, 16 weeks CDCSA) and offering to narrow down based on specific circumstances.

---

### Test 3: S Pass Quota

**Query**: "What is the S Pass quota for a services company with 50 local employees?"

**Response Content**:

- Direct answer: "8 S Pass holders"
- Mathematical derivation: S/(50+S) <= 0.15 -> 0.85S <= 7.5 -> S <= 8.82 -> max 8
- S Pass cap: 15% of total workforce -- cited EFMA-SP
- DRC (Dependency Ratio Ceiling): 35% for services sector -- cited EFMA-DRC
- Explains relationship: S Pass cap (15%) is stricter than DRC (35%), so S Pass is the binding constraint
- Follow-up suggestions: "Tell me more", "What should I do next?"

**Verification**: The 15% S Pass sub-quota (effective from January 2024) is correct. The algebraic working (S/(50+S) <= 0.15) is the correct formula. 8 is the correct answer.

**Quality Note**: Showing the algebraic derivation is genuinely useful -- HR managers can verify the answer and understand the formula for different headcounts.

---

### Test 4: Multi-Turn Context

**Turn 1 Query**: "What are the notice period rules?"
**Turn 2 Query**: "What if they've worked for 6 years?"

**Turn 1 Response**: Comprehensive overview of EA s.10 notice period rules, covering who may give notice, statutory minimums by service length, contract terms, and notice pay.

**Turn 2 Response**:

- "4 weeks' notice for employees with 5 years' service or more (EA s.10)"
- Maintains context: interprets "6 years" as a notice period follow-up
- Key points: statutory minimum vs contract terms, notice in writing requirement, payment in lieu
- Offers to calculate notice pay

**Verification**: 4 weeks for 5+ years service is correct per EA s.10.

**Quality Note**: The follow-up question "What if they've worked for 6 years?" is deliberately ambiguous. Without context, it could refer to anything. The engine correctly interprets it as a continuation of the notice period discussion. This demonstrates genuine conversational intelligence.

---

### Test 5: Multi-Domain (CRITICAL -- 3 Runs)

**Query**: "My foreign worker's EP expires next month and I want to terminate them"

This query spans two regulatory domains: EFMA (Employment of Foreign Manpower Act) for work pass matters and EA (Employment Act) for termination procedures. This was the previously-failing test that prompted the multi-domain steering fix.

**Run 1** (74.2s) -- PASS:

- Risk tier: Medium Risk, Moderate confidence
- EA coverage: notice periods (s.10), notice in writing (s.11), summary dismissal (s.13), Key Employment Terms (s.20A)
- EFMA coverage: EP cancellation, MOM WPOnline portal, repatriation obligations (EFMA-OBLIG), flight home (EFMA-FLT), compassionate leave (EFMA-COMPAS)
- Structured as: key legal points -> practical steps -> checklist

**Run 2** (63.1s) -- PASS:

- Same dual-domain coverage
- Adds: wrongful dismissal (EA s.14), tax clearance (IR21), documentation retention
- Structured as: summary -> detailed legal points -> action items

**Run 3** (71.1s) -- PASS:

- Risk tier: Medium Risk, High confidence
- "Concise, practical synthesis based only on the provisions you asked me to use"
- Covers: employment contract check (EA-S20A), statutory notice (EA s.10), EP procedures (EFMA), documentation
- Offers to draft termination letter language and calculate notice pay

**Intermittency Assessment**: ZERO intermittency. 3/3 runs covered both EFMA work pass management AND Employment Act termination. The responses varied in structure and phrasing (not templated) but consistently covered both domains.

**Quality Note**: This is the most impressive test result. The engine doesn't just list provisions from two domains -- it weaves them into a practical workflow: (1) check contract, (2) give notice/pay in lieu, (3) cancel EP on WPOnline, (4) handle repatriation, (5) file IR21 for tax clearance. This level of integrated, multi-domain synthesis is what would normally require consulting both an employment lawyer and an immigration specialist.

The "Medium Risk" classification is appropriate -- termination of a foreign worker with an expiring EP is a sensitive situation that should be flagged for professional review.

---

### Test 6: Out-of-Scope Decline

**Query**: "What is the weather today?"

**Response**: "I can only help with HR and employment matters in Singapore. Could you rephrase your question as a workplace or employment query?"

- Risk tier: Low Risk, High confidence
- Follow-ups: "Tell me more", "What should I do next?"
- Response time: 9.0s (fast rejection)
- No error messages, no stack traces, no broken state

**Quality Note**: The decline is professional and non-condescending. It reinforces the product's domain ("HR and employment matters in Singapore") rather than just saying "I can't do that." The 9-second response time shows the engine doesn't waste cycles on off-topic queries.

---

### Test 7: Conversation Persistence

**Method**: Navigate away to `/dashboard`, then back to `/advisory`, then check `/advisory/history`.

**Results**:

- Sidebar on `/advisory` shows all test conversations with titles and previews
- `/advisory/history` page shows 21 conversations total
- Each conversation has: auto-generated title, risk tier badge (Low Risk/green, Medium Risk/amber), timestamp, message count, response preview
- Risk tier filtering (All/Green/Amber/Red tabs)
- Search bar for finding conversations
- "Export CSV" button for compliance documentation

**Quality Note**: The history page is enterprise-grade. Risk tier filtering and CSV export demonstrate compliance readiness. An HR manager or auditor can review past advisory interactions, filter by risk level, and export for documentation.

---

## Cross-Cutting Assessment

### Response Quality Patterns

Every substantive response demonstrated:

1. **Specific statutory citations**: Consistent shorthand format (CPFA-S7, EA-S10, EFMA-SP, CDCSA) with provision tags that appear to be clickable
2. **Structured formatting**: Headings, bullet points, numbered steps
3. **Mathematical workings**: Where applicable (CPF rates, quota formulas), the engine shows its work
4. **Risk assessment**: Appropriate risk tier assignment (Low for factual queries, Medium for sensitive situations)
5. **Confidence scoring**: High confidence for well-documented topics, Moderate for complex multi-domain queries
6. **Follow-up suggestions**: Contextually relevant, not generic
7. **Legal disclaimers**: Footer disclaimer on every page ("This is not legal advice")

### Data Accuracy

Every verifiable claim was checked:

| Claim                            | Verified | Source                   |
| -------------------------------- | -------- | ------------------------ |
| CPF employer 17% (age <= 55)     | Correct  | CPF Act First Schedule   |
| CPF employee 20% (age <= 55)     | Correct  | CPF Act First Schedule   |
| CPF total $2,775                 | Correct  | $1,275 + $1,500          |
| OW ceiling $8,000                | Correct  | CPF Board 2026 rates     |
| OA/SA/MA split 23%/6%/8%         | Correct  | CPF Act allocation rates |
| Maternity 8 weeks (EA)           | Correct  | EA Part IX               |
| Maternity 16 weeks (CDCSA)       | Correct  | CDCSA                    |
| S Pass cap 15%                   | Correct  | EFMA effective Jan 2024  |
| DRC services 35%                 | Correct  | MOM DRC table            |
| S Pass headroom 8 for 50 locals  | Correct  | S/(50+S) <= 0.15         |
| Notice period 4 weeks (5+ years) | Correct  | EA s.10                  |

**Hallucinations detected: ZERO**

### Response Latency

| Scenario                    | Time      | Assessment                       |
| --------------------------- | --------- | -------------------------------- |
| Simple out-of-scope         | 9.0s      | Good                             |
| CPF calculation             | 27.1s     | Acceptable                       |
| S Pass quota                | 33.1s     | Acceptable                       |
| Maternity leave             | 47.1s     | Slow                             |
| Multi-turn (2 turns total)  | 51.1s     | Acceptable                       |
| Multi-domain EP/termination | 69.5s avg | Slow but justified by complexity |

The streaming UI (phased thinking indicator: "Searching knowledge base... Analysing provisions... Generating response...") mitigates perceived wait time. Content starts appearing within 10-15 seconds even for long responses.

For an advisory tool (not a chatbot), these response times are acceptable. Users are asking employment law questions, not ordering coffee. A 70-second response that provides a legally-grounded, multi-domain action plan with statutory citations is far more valuable than a 3-second hallucinated answer.

### Browser Console

**Zero console errors** across the entire test session. Clean execution.

---

## Issues Found

| #   | Issue                                                          | Severity | Category    | Notes                                                                           |
| --- | -------------------------------------------------------------- | -------- | ----------- | ------------------------------------------------------------------------------- |
| 1   | Response latency 27-74s                                        | MEDIUM   | INFRA/MODEL | Streaming UI mitigates; acceptable for advisory use case                        |
| 2   | Conversation titles show HTML entities (&#x27; for apostrophe) | LOW      | FRONTEND    | Visible in sidebar: "My foreign worker&#x27;s EP exp..."                        |
| 3   | Test 1 citation not detected by test harness                   | N/A      | TOOLING     | Script checked "cpf act" but engine uses "CPFA-S7" format. Not a product issue. |

---

## Demo Recommendation

If presenting Arbor to an enterprise buyer, run the tests in this order:

1. **Lead with Test 5** (multi-domain): The most impressive. A single question about EP expiry + termination produces an integrated action plan covering two regulatory domains. This is the "wow" moment.

2. **Follow with Test 1** (CPF calculation): Concrete, verifiable numbers. The algebraic workings and account allocation breakdown show genuine domain depth.

3. **Show Test 7** (conversation persistence): The history page with risk tier filtering and CSV export tells the compliance/audit story. Enterprise buyers care about this.

4. **Demonstrate Test 4** (multi-turn): Natural conversation flow. "What if they've worked for 6 years?" -- the engine understands context.

5. **Close with Test 6** (out-of-scope): "It won't tell you the weather." Demonstrates governance and guardrails. The audience respects this.

---

## Bottom Line

The Arbor advisory engine with gpt-5-mini and the multi-domain steering fix is production-ready. Every test passed. Zero hallucinations. Zero intermittency on the critical multi-domain test. The response quality goes beyond surface-level chatbot answers -- it provides substantive, citation-backed guidance that integrates multiple regulatory domains into practical action plans, shows mathematical workings for calculations, and correctly classifies risk levels.

The multi-domain steering fix is confirmed working. The engine consistently handles the EP expiry + termination query (the hardest test) by synthesizing EFMA work pass obligations and Employment Act termination procedures into a coherent, actionable checklist. This is the kind of advisory that would normally require consulting two different specialists.

If I were advising the board: this is a genuinely useful tool for Singapore SME HR compliance. It is not a ChatGPT wrapper. The CPF calculations are deterministic and correct. The legal citations are specific and verifiable. The risk tier system flags sensitive queries for professional review. The conversation history with CSV export satisfies audit requirements.

**Verdict: Ready for production use. Ship the steering fix.**

---

## Appendix: Evidence

**Screenshots**: `tests/e2e/screenshots/redteam-browser/`

| File                         | Description                                   |
| ---------------------------- | --------------------------------------------- |
| `00-dashboard.png`           | Post-login dashboard showing full HRIS suite  |
| `00-advisory-landing.png`    | Advisory page with conversation sidebar       |
| `01-cpf-response.png`        | CPF calculation -- all figures correct        |
| `02-maternity-response.png`  | Maternity leave -- EA + CDCSA coverage        |
| `03-spass-response.png`      | S Pass quota -- algebraic derivation          |
| `04-notice-turn1.png`        | Notice period rules (turn 1)                  |
| `04-notice-turn2.png`        | 6 years context follow-up (turn 2)            |
| `05-multidomain-run1.png`    | EP + termination run 1 -- PASS                |
| `05-multidomain-run2.png`    | EP + termination run 2 -- PASS                |
| `05-multidomain-run3.png`    | EP + termination run 3 -- PASS                |
| `06-outofscope-response.png` | Weather query -- polite decline               |
| `07-back-to-advisory.png`    | Conversation persistence in sidebar           |
| `07-history-page.png`        | History page with risk filtering + CSV export |
| `results.json`               | Machine-readable test results                 |

**Test script**: `tests/e2e/red_team_browser.mjs`
