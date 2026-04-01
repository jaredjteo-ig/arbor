# Critical Demo Warnings & Pre-Flight Checklist

**Date**: 2026-03-24
**Source**: Combined findings from deep-analyst and value-auditor agents

---

## Warning: Multi-Jurisdiction Guardrail Will Reject Thai Questions

The guardrails in `src/hr_advisory/workflows/guardrails.py` (line 364) trigger a `MULTI_JURISDICTION` escalation on patterns matching "cross-border", "overseas", "foreign jurisdiction", or "international employment."

**If someone asks a Thailand-specific question during the demo, the system will flag it as requiring escalation.** This would make Central look like it is rejecting the audience's use case.

**Mitigation**: Only ask Singapore employment law questions during the live demo. Frame Thai questions as "what this would look like" — never type them into the system.

---

## Warning: $5/Month Budget Cap

The advisory engine has a per-company monthly budget cap of $5 by default (via `CompanyLLMConfig`). Demo prep queries will count against this.

**Mitigation**: Before the demo, either:

- Set the demo company's budget to $50+ via the admin panel
- Use a BYOK API key (which bypasses budget tracking)
- Verify the budget hasn't been exhausted from testing

---

## Warning: Conversations Are In-Memory

Advisory conversations are stored in-memory with LRU eviction (10K conversations). A server restart wipes them.

**Mitigation**: If you prep demo conversations, note that a redeploy will clear them. Either:

- Prep conversations right before the demo
- Accept that you'll start fresh conversations during the demo (which is fine — it shows the real flow)

---

## Pre-Flight Checklist (24 Hours Before Demo)

### Infrastructure

- [ ] Verify `central.kailash.ai` returns 200 on `/api/health`
- [ ] Verify SSL certificate is valid
- [ ] Check server uptime — run `curl -s https://central.kailash.ai/api/health | python3 -m json.tool`
- [ ] Deploy latest code if needed — 5 commits since last deploy include SSE fixes and KB search fallback improvements

### API & Budget

- [ ] Verify Gemini API key (GOOGLE_API_KEY) on server is valid
- [ ] Have a backup Gemini API key ready
- [ ] Set demo company budget to $50+ (or plan to use BYOK)
- [ ] Test one advisory query end-to-end to confirm streaming works

### Demo Account

- [ ] Create demo user account
- [ ] Create demo company with realistic name (e.g. "Central Solutions Pte Ltd" — Singapore company to match the KB)
- [ ] Add 10-20 demo employees with varied profiles
- [ ] Run at least one payroll calculation to show payroll history
- [ ] Create a few leave applications (some approved, some pending)
- [ ] Submit a couple of claims

### Advisory Prep

- [ ] Pre-test the 5 scripted advisory questions (see demo script)
- [ ] Verify each returns proper citations and risk tiers
- [ ] Time the responses — first query with tool calls takes 5-8 seconds
- [ ] Pre-warm the system with one query before the audience arrives

### Avoid List (Memorize These)

- [ ] Do NOT ask Thailand-specific questions (triggers MULTI_JURISDICTION escalation)
- [ ] Do NOT show the Analytics page if empty
- [ ] Do NOT show the Clients page ("View" button is a dead end per Value Audit)
- [ ] Do NOT show the cold-start dashboard (go to pre-seeded account)
- [ ] Do NOT dwell on Singapore jargon without translating to Thai equivalents
- [ ] Do NOT position as "ready for Thailand today" — position as "the architecture that will power Thailand"

---

## Scripted Advisory Questions (Tested Safe)

These questions are designed to showcase different capabilities:

1. **Simple factual + citation** — "What is the minimum notice period for terminating an employee who has worked for 3 years?"
   - Expected: Employment Act Section 10, clear answer with citation

2. **Calculator trigger** — "What are the CPF contribution rates for a 35-year-old Singapore citizen earning $5,000?"
   - Expected: Calls `calculate_cpf` tool, returns exact rates from CPF Act Section 7

3. **Multi-domain** — "An employee was injured at work. What are my obligations as an employer?"
   - Expected: Cross-references WSH Act and WICA, multi-domain response

4. **Edge case / Red tier** — "An employee claims they were wrongfully dismissed after refusing to work overtime. What should I do?"
   - Expected: RED risk tier, professional referral recommendation, detailed process

5. **Proactive compliance** — "I'm hiring a foreign worker for the first time. What do I need to know?"
   - Expected: Calls `calculate_quota_levy`, references EFMA, comprehensive onboarding guide

---

## Key Insight for Japanese MNC Audience

The deep-analyst and value-auditor both independently flagged the same point: **EATP trust lineage is the single strongest "wow" for a Japanese corporate audience.**

Japanese MNC culture places extreme value on traceability, auditability, and process rigor. When you show that every AI advisory response carries:

- A cryptographic genesis record
- Agent attestations showing which specialist contributed
- A constraint envelope showing what the AI was and was not allowed to do
- Risk-tier classification with escalation triggers

...you are speaking the language of Japanese corporate governance. **No competitor in the Thai HR SaaS market offers this.**

The emergency response module is the second strongest differentiator — structured crisis management with deadlines, document checklists, and escalation workflows. For a company with service engineers in the field, this has immediate practical value.
