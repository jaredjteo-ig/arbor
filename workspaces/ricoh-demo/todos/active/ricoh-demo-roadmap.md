# Ricoh Thailand Demo — Active Roadmap

**Status**: Demo delivered 2026-03-28. M1–M4, M6 complete. See `todos/completed/ricoh-demo-m1-m6-completed.md`.
**Platform**: central.kailash.ai (AWS EC2, ap-southeast-1)

---

## Production Hardening — COMPLETE (2026-04-06)

Verified on GCP (136.110.51.61):

### T027: COMPLETE — 5 scripted advisory questions

- Q1 (notice period): PASS — 9.4s, 5 citations, 739 chars
- Q2 (CPF rates): PASS — 6.5s, correct 20%/$1,000
- Q3 (workplace injury): PASS — safety chain cautious response (prompt tuning opportunity)
- Q4 (wrongful dismissal): PASS — RED tier, litigation referral
- Q5 (foreign worker): PASS — safety chain cautious response (prompt tuning opportunity)

### T029: COMPLETE — Conversation persistence

- Conversation created, follow-up works, history loads, listed in conversations

### T030: COMPLETE — Latency baseline

- Average: 5.4s (Gemini 2.5 Flash), all under 8s target

---

## M8: Thailand Proof-of-Concept (Post-Demo)

Activates if Ricoh agrees to PoC engagement. Estimated 3-4 weeks.

### T039: Build minimal Thai KB (10-20 provisions)

New `src/hr_advisory/kb/content/thai_labour.py`. Key provisions:

- Severance pay (LPA Section 118): 30-400 days by tenure
- Annual leave minimum (LPA Section 30): 6 days after 1 year
- Overtime rates (LPA Sections 61/63): 1.5x normal, 3x holiday
- Notice period (LPA Section 17): at least one pay cycle
- Working hours (LPA Section 23): 8 hours/day, 48 hours/week
- Maternity leave (LPA Section 41): 98 days
- Sick leave (LPA Section 32): 30 working days/year
- Social Security contributions: 5%/5%, capped THB 750 each

### T040: Build Thai Social Security Fund calculator

New `src/hr_advisory/workflows/calculators/ssf_calculator.py`

- Employer: 5% of wages capped at THB 15,000/month = max THB 750
- Employee: same
- Handle temporary rate reductions

### T041: Build Thai PIT withholding calculator

New `src/hr_advisory/workflows/calculators/thai_pit_calculator.py`

- Progressive brackets: 0% (up to 150K) → 5% → 10% → 15% → 20% → 25% → 30% → 35%
- Monthly withholding = (projected annual tax) / 12
- Handle deductions (personal 60K, spouse 60K, children 30K, social security, etc.)

### T042: Build Thai severance calculator

New `src/hr_advisory/workflows/calculators/thai_severance_calculator.py`

- LPA Section 118 scale: 30/90/180/240/300/400 days by tenure band

### T043: Build Thai specialist agents (3 priority domains)

1. Labour Protection specialist — Thai LPA (equivalent of EA)
2. Social Security specialist — Thai SSF (equivalent of CPF)
3. Tax specialist — Thai Revenue Code (equivalent of IRAS)

### T044: Thai guardrail patterns

Add Thai-specific circumvention detection to `guardrails.py`:

- "Avoid paying social security contributions" → illegal under SSA
- "Pay below minimum wage" → violation of LPA
- "Hire foreign worker without permit" → violation of Working of Aliens Act

### T045: Engage Thai legal counsel for KB validation

- Recommended: Chandler MHM (Japanese-Thai firm)
- Scope: Review 3 domain KB modules
- Budget: THB 50,000-150,000

---

## M9: Multi-Jurisdiction Architecture (Long-term)

Only if Ricoh engagement proceeds AND multi-country is on the table. Estimated 2-3 months.

### T046: Add jurisdiction field to Company model

### T047: Parameterize calculators by jurisdiction

### T048: Jurisdiction-aware domain routing

### T049: Bilingual advisory (Thai + English)

### T050: Thai statutory filing formats

### T051: Full Thai calculator suite

### T052: ASEAN expansion framework

---

## Summary

| Section                | Todos            | Status                    | Priority  |
| ---------------------- | ---------------- | ------------------------- | --------- |
| Production Hardening   | T027, T029, T030 | **COMPLETE**              | DONE      |
| M8: Thailand PoC       | T039-T045        | Blocked on Ricoh decision | POST-DEMO |
| M9: Multi-jurisdiction | T046-T052        | Future                    | POST-DEMO |

**14 remaining todos**: 7 Thailand PoC (blocked on Ricoh decision) + 7 multi-jurisdiction (future). 45 completed or obsolete.
