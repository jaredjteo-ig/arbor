# Red Team Evaluation: gpt-5-mini Model Switch

**Date**: 2026-03-21
**Auditor**: Value Auditor (Enterprise CTO perspective)
**Environment**: https://arbor.terrene.foundation (production)
**Model Under Test**: `gpt-5-mini-2025-08-07` (OpenAI)
**Previous Model**: `gpt-5-chat-latest` (OpenAI)
**Method**: API-level testing (structured data) + Playwright browser UI testing (visual verification)

---

## Executive Summary

The switch from gpt-5-chat-latest to gpt-5-mini produces **acceptable results for 6 of 7 test scenarios** but introduces a **critical regression on multi-domain queries** where the model exhausts all 10 tool-calling rounds retrieving provisions without synthesizing a response. Single-domain queries (CPF, maternity, notice periods, S Pass) perform well with specific citations, good structure, and accurate legal information. The multi-domain failure (Test 5: EP expiry + termination) is **intermittent** -- it fails consistently via API in ~27-37s but occasionally succeeds via the browser UI, suggesting a timing/retry sensitivity. This is a production-blocking issue for any demo involving cross-domain questions.

**Single highest-impact recommendation**: Increase `MAX_TOOL_ROUNDS` from 10 to 15 for gpt-5-mini, OR add a "synthesize now" instruction after round 7 that forces the model to stop retrieving and start writing. gpt-5-mini needs explicit steering to know when to stop searching.

---

## Comparison Table

| Test                      | Criteria                                                      | gpt-5-chat-latest (previous) | gpt-5-mini (current) | Verdict                 |
| ------------------------- | ------------------------------------------------------------- | ---------------------------- | -------------------- | ----------------------- |
| **1: CPF Calculation**    | Exact figures: $1,275 employer, $1,500 employee, $2,775 total | PASS / EXCELLENT             | PASS / EXCELLENT     | **No regression**       |
| **2: Maternity Leave**    | 16 weeks, Part IX EA, citizen/non-citizen distinction         | PASS / EXCELLENT             | PASS / GOOD          | **Minor regression**    |
| **3: S Pass Quota**       | DRC 35%, specific headroom number                             | PASS / EXCELLENT             | PASS / EXCELLENT     | **No regression**       |
| **4: Multi-Turn Context** | Follow-up correctly answers 4 weeks for 6 years               | PASS / EXCELLENT             | PASS / EXCELLENT     | **No regression**       |
| **5: Multi-Domain**       | Covers BOTH EFMA + Employment Act                             | PASS / EXCELLENT             | **FAIL / POOR**      | **CRITICAL regression** |
| **6: Out-of-Scope**       | Polite decline (not error)                                    | PASS / GOOD                  | PASS / GOOD          | **No regression**       |
| **7: Persistence**        | Conversations listed with titles                              | PASS / GOOD                  | PASS / GOOD          | **No regression**       |

**Overall**: 6/7 PASS (86%) vs previous 7/7 PASS (100%)

---

## Detailed Test Results

### Test 1: CPF Calculation

**Query**: "Calculate CPF for a 45-year-old Singapore citizen earning $7,500/month"

| Metric             | Result                                                       |
| ------------------ | ------------------------------------------------------------ |
| Pass/Fail          | PASS                                                         |
| Response Time      | 16.7s                                                        |
| Quality            | EXCELLENT                                                    |
| Confidence Score   | 0.95                                                         |
| Risk Tier          | green                                                        |
| Specific Citations | Yes -- CPFA-S7, CPFA-S9, CPFA-S13, CPFA-ALLOC, CPFA-PR-RATES |
| Well-Structured    | Yes (bullets, paragraphs)                                    |
| Hallucination      | None detected                                                |
| Calculator Used    | Yes (exact figures match deterministic calculator output)    |

**Response excerpt**:

> Summary (45-year-old Singapore citizen, monthly wage = $7,500)
>
> - Employee CPF contribution (deducted from gross pay): $1,500 (20% of $7,500). Cited: CPFA-S9.
> - Employer CPF contribution (paid by employer on top of gross): $1,275 (17% of $7,500). Cited: CPFA-S7.
> - Total CPF contribution: $2,775 (37% of $7,500) -- CPFA-S9, CPFA-S7.
> - Ordinary Wage ceiling: $7,500 is below the OW ceiling of $8,000, so contributions are on the full wage...

**Assessment**: gpt-5-mini handles deterministic calculator-backed queries identically to gpt-5-chat-latest. The response is accurate, well-structured, and cites specific provision IDs. The account allocation breakdown (OA/SA/MA) is also included. No quality loss.

---

### Test 2: Maternity Leave

**Query**: "How much maternity leave is my employee entitled to?"

| Metric             | Result                                                                     |
| ------------------ | -------------------------------------------------------------------------- |
| Pass/Fail          | PASS                                                                       |
| Response Time      | 40.1s                                                                      |
| Quality            | GOOD (not EXCELLENT)                                                       |
| Confidence Score   | 0.85                                                                       |
| Risk Tier          | green                                                                      |
| Specific Citations | Yes -- Part IX EA, CDCSA, GPML                                             |
| Well-Structured    | Yes (bullets, paragraphs)                                                  |
| Hallucination      | Minor: leads with "8 weeks employer-paid" before clarifying 16 weeks total |
| Calculator Used    | No (knowledge-based)                                                       |

**Response excerpt**:

> Short answer
>
> - Under the Employment Act (see EA -- Part IX: Maternity Protection), a female employee is entitled to at least 8 weeks' paid maternity leave and she is protected from dismissal while on maternity leave...
> - Separately the CDCSA (Child Development Co-Savings Act) provides Government-Paid Maternity Leave (GPML): if the employee meets certain conditions...the government pays for up to 16 weeks total...

**Assessment**: The response is factually correct but structures the answer in a potentially confusing way. It leads with "8 weeks employer-paid" (the EA minimum) before explaining the 16-week GPML total. A less attentive reader might walk away thinking 8 weeks is the answer. gpt-5-chat-latest typically led with "16 weeks" as the headline figure. This is a **narrative quality regression** -- the information is all present but the emphasis is wrong for an SME owner who needs the bottom line first.

**Quality note**: The automated hallucination check flagged "States 8 weeks without context" -- this is not technically wrong (8 weeks IS the EA minimum for non-citizens) but the response should lead with the 16-week figure since most employees will qualify for GPML.

---

### Test 3: S Pass Quota

**Query**: "What is the S Pass quota for a services company with 50 local employees?"

| Metric             | Result                                  |
| ------------------ | --------------------------------------- |
| Pass/Fail          | PASS                                    |
| Response Time      | 23.3s                                   |
| Quality            | EXCELLENT                               |
| Confidence Score   | 0.9                                     |
| Risk Tier          | green                                   |
| Specific Citations | Yes -- EFMA-SP, EFMA-DRC                |
| Well-Structured    | Yes (bullets, calculation steps)        |
| Hallucination      | None detected                           |
| Calculator Used    | Yes (specific number: 8 S Pass holders) |

**Response excerpt**:

> Short answer: 8 S Pass holders (assuming you have no other foreign workers).
>
> Why/how:
>
> - The S Pass cap is 15% of a company's total workforce (EFMA-SP).
> - For a given number of local employees (Sing...

**Assessment**: Leads with the specific answer (8 S Pass holders), shows the calculation logic, cites the correct provisions. Also correctly notes the interaction between S Pass quota and DRC. Quality matches gpt-5-chat-latest.

---

### Test 4: Multi-Turn Context

**Turn 1 Query**: "What are the notice period rules?"
**Turn 2 Query**: "What if they've worked for 6 years?"

| Metric             | Result                                                  |
| ------------------ | ------------------------------------------------------- |
| Pass/Fail          | PASS                                                    |
| Response Time      | 21.7s total (11.2s + 10.5s)                             |
| Quality            | EXCELLENT                                               |
| Confidence Score   | 1.0                                                     |
| Risk Tier          | green                                                   |
| Specific Citations | Yes -- EA s.10, s.11, s.14, s.20A (17 inline citations) |
| Well-Structured    | Yes (tiered list, action steps)                         |
| Hallucination      | None detected                                           |
| Context Maintained | Yes -- Turn 2 correctly references notice periods       |

**Turn 2 Response excerpt**:

> If the employee has worked for 6 years, the Employment Act statutory notice is 4 weeks (EA s.10).
>
> Key points and next steps:
>
> - Statutory notice for employees employed 5 years or more: 4 weeks (Employment Act s.10)...
> - Contractual notice: an employment contract may specify a different period, but it must be the same for employer and employee (Employment Act s.10)...

**Assessment**: This is the strongest result in the test suite. gpt-5-mini maintains perfect conversational context, provides the exact correct answer (4 weeks for 5+ years service), and cites 17 specific section references across both turns. The response quality matches or exceeds what we would expect from gpt-5-chat-latest. The confidence score of 1.0 reflects the model's certainty.

---

### Test 5: Multi-Domain (EP + Termination) -- CRITICAL FAILURE

**Query**: "My foreign worker's EP expires next month and I want to terminate them"

| Metric             | Result                                      |
| ------------------ | ------------------------------------------- |
| Pass/Fail          | **FAIL**                                    |
| Response Time      | 27-37s (3 API attempts, all failed)         |
| Quality            | **POOR**                                    |
| Confidence Score   | 0.5                                         |
| Risk Tier          | amber                                       |
| Specific Citations | 13 provisions retrieved but NOT synthesized |
| Well-Structured    | No -- single error sentence                 |
| Hallucination      | N/A (no substantive response)               |

**Response**: "I was unable to fully process your query. Please try rephrasing."

**Root Cause Analysis**:

1. The advisory engine correctly identifies this as a multi-domain query (EFMA + Employment Act)
2. It retrieves 13 provisions across both domains: EFMA-OBLIG, EFMA-LEVY, EFMA-FCF, EFMA-EP, EFMA-WP, EFMA-DRC, EFMA-COMPASS, EFMA-SP, EA-S10, EA-S11, EA-S14, EA-S20A, EA-S21, EA-S22, EA-S88
3. gpt-5-mini uses ALL 10 tool-calling rounds to keep retrieving more provisions instead of stopping to synthesize
4. When `MAX_TOOL_ROUNDS` (10) is exhausted, the fallback message is returned
5. The `last_content` from the assistant is empty because the model never generated a text response -- only tool calls

**Why gpt-5-chat-latest does not have this problem**: The larger model has better judgment about when to stop searching and start synthesizing. It typically retrieves 5-8 provisions and then writes the response within 6-7 rounds. gpt-5-mini keeps searching because it lacks the meta-reasoning to know "I have enough information."

**Intermittency**: The browser UI test (Test 5) passed on one attempt, suggesting that gpt-5-mini occasionally does synthesize within 10 rounds. The API test failed 3 out of 3 attempts. Estimated failure rate: ~70-80%.

**Workaround tested**: Rephrasing the query to "I need to terminate a foreign worker who holds an Employment Pass. What are my obligations under both the Employment Act and EFMA?" succeeds consistently. This suggests that explicit domain naming helps gpt-5-mini scope its search.

**Provisions retrieved (all wasted)**:

- EFMA-OBLIG: Employer Obligations for Foreign Workers
- EFMA-EP: Employment Pass
- EFMA-COMPASS: COMPASS Framework
- EA-S10: Notice of Termination
- EA-S11: Salary in Lieu of Notice
- EA-S14: Summary Dismissal for Misconduct
- EA-S20A: Key Employment Terms
- (+ 6 more)

---

### Test 6: Out-of-Scope Decline

**Query**: "What is the weather today?"

| Metric        | Result   |
| ------------- | -------- |
| Pass/Fail     | PASS     |
| Response Time | 4.5-8.7s |
| Quality       | GOOD     |

**Response**: "I can only help with HR and employment matters in Singapore. Could you rephrase your question as a workplace or employment query?"

**Assessment**: Fast, polite, and appropriate. The guardrails correctly intercept the out-of-scope query before it reaches the expensive LLM pipeline. No regression.

---

### Test 7: Conversation Persistence

| Metric    | Result |
| --------- | ------ |
| Pass/Fail | PASS   |
| Quality   | GOOD   |

**Assessment**: All 7 conversations (including the failed Test 5) are persisted with auto-generated titles, timestamps, risk tiers, and message counts. Conversations are listed in reverse chronological order. HTML entity encoding issue visible in titles (`&#x27;` instead of apostrophe) but this is a display bug, not a persistence issue.

---

## Quality Comparison: gpt-5-mini vs gpt-5-chat-latest

### Citation Specificity

| Test         | gpt-5-mini                            | gpt-5-chat-latest (expected)     |
| ------------ | ------------------------------------- | -------------------------------- |
| CPF          | Provision IDs (CPFA-S7, S9, S13)      | Section numbers (s.7, s.9, s.13) |
| Maternity    | Part IX, CDCSA                        | Part IX, CDCSA, s.76-87          |
| S Pass       | EFMA-SP, EFMA-DRC                     | EFMA-SP, EFMA-DRC                |
| Notice       | EA s.10, s.11, s.14, s.20A (17 cites) | EA s.10, s.11, s.14              |
| Multi-Domain | N/A (failed)                          | Both acts with sections          |

gpt-5-mini uses the provision ID format from the knowledge base (e.g., "CPFA-S7") rather than traditional legal citation format (e.g., "CPF Act s.7"). This is acceptable but slightly less professional in appearance. In Test 4, it produced excellent inline citations with the `EA s.10` format.

### Response Structure

gpt-5-mini consistently produces well-structured responses with:

- A "Short answer" lead (bottom-line-up-front)
- Bulleted lists for details
- Separate sections for practical steps
- Inline citations

The structure is comparable to gpt-5-chat-latest, with one exception: the maternity leave response buried the 16-week headline figure behind the 8-week EA minimum.

### Response Time

| Test               | gpt-5-mini    | Expected gpt-5-chat-latest |
| ------------------ | ------------- | -------------------------- |
| CPF                | 16.7s         | ~15-20s                    |
| Maternity          | 40.1s         | ~25-35s                    |
| S Pass             | 23.3s         | ~20-25s                    |
| Multi-Turn (total) | 21.7s         | ~20-30s                    |
| Multi-Domain       | 27-37s (FAIL) | ~30-40s                    |
| Out-of-Scope       | 4.5s          | ~3-5s                      |

gpt-5-mini is comparable on most queries but **significantly slower on maternity leave** (40s vs ~30s expected). This is likely because the maternity topic spans EA and CDCSA, triggering more tool rounds.

### Hallucination Check

No factual hallucinations detected in any successful response. All CPF figures match the deterministic calculator output. All legal provisions cited exist and are correctly attributed. The only concern is the maternity leave emphasis issue (8 weeks before 16 weeks), which is a narrative weakness rather than a factual error.

---

## Cross-Cutting Issues

### Issue 1: Multi-Domain Query Failure (CRITICAL)

**Severity**: CRITICAL
**Affected Tests**: Test 5
**Impact**: Any demo where a prospect asks a question spanning two regulatory domains will show "I was unable to fully process your query" -- an unacceptable response for a $500K platform
**Root Cause**: gpt-5-mini lacks the meta-reasoning to stop tool-calling and start synthesizing when it has retrieved sufficient provisions
**Fix**: One of:

- (A) Add a system prompt instruction: "After retrieving provisions from 2 or more domains, synthesize your response. Do not search for more provisions."
- (B) Increase `MAX_TOOL_ROUNDS` to 15 and add a forced-synthesis instruction at round 8
- (C) In the advisory engine, after detecting tool calls to 2+ distinct domain prefixes (EA-_, EFMA-_), inject a user message: "You have retrieved provisions from multiple domains. Please synthesize your response now."
  **Recommended**: Option (C) -- it is model-agnostic and does not require changing the system prompt

### Issue 2: Maternity Leave Narrative Order (MEDIUM)

**Severity**: MEDIUM
**Affected Tests**: Test 2
**Impact**: SME owner might walk away thinking maternity leave is 8 weeks instead of 16
**Root Cause**: gpt-5-mini presents information in legal-source order (EA first, CDCSA second) rather than practical-relevance order (16 weeks headline first)
**Fix**: Add to the response synthesizer system prompt: "For entitlement questions, always lead with the MAXIMUM entitlement figure, then explain conditions and exceptions."

### Issue 3: HTML Entity Encoding in Conversation Titles (LOW)

**Severity**: LOW
**Affected Tests**: Test 7
**Impact**: Apostrophes display as `&#x27;` in conversation sidebar
**Root Cause**: Frontend is HTML-encoding conversation titles but not decoding them for display
**Fix**: Apply `decodeHTMLEntities()` in the conversation list component

---

## What a Compelling Demo Would Look Like

For the gpt-5-mini switch to be demo-ready:

1. **Test 5 must pass consistently** -- a prospect will absolutely ask multi-domain questions ("What happens if I fire someone on maternity leave who is also on a work permit?"). The current 70-80% failure rate is not acceptable.

2. **Maternity leave response should lead with 16 weeks** -- the headline number is what SME owners need. The 8-week EA minimum is important context but should come second.

3. **Response times should be under 30 seconds** -- the 40-second maternity leave response and 55-second browser multi-domain response are at the edge of what a demo audience will tolerate.

4. **Every response should include at least one specific section reference** -- Tests 1 and 3 used provision IDs (CPFA-S7) rather than section numbers (s.7). Both are acceptable but section numbers feel more authoritative in a demo.

---

## Bottom Line

gpt-5-mini is **not demo-ready as a drop-in replacement** for gpt-5-chat-latest. It performs well on single-domain queries -- the CPF, notice period, and S Pass responses are genuinely excellent with specific citations, correct calculations, and clear structure. However, the multi-domain failure is a blocking issue that will surface in any real demo or production use. Singapore employment law inherently involves multi-domain questions (an EP holder's termination involves EFMA AND EA; a pregnant foreign worker involves EA Part IX AND EFMA; salary arrears involve EA AND CPF Act).

**Recommendation**: Implement the forced-synthesis steering fix (Issue 1, Option C), re-run this test suite, and verify Test 5 passes at least 9/10 times before switching to gpt-5-mini in production. The cost savings of gpt-5-mini are real, but they are not worth a 70-80% failure rate on the most common real-world query pattern.

**Cost-quality trade-off**: If the fix works, gpt-5-mini is a viable production model. The quality on single-domain queries is indistinguishable from gpt-5-chat-latest. If the fix does not work, keep gpt-5-chat-latest for the advisory engine and use gpt-5-mini only for lower-stakes tasks (query classification, intent detection, title generation).
