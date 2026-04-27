# Recruitment Module: Value Audit

**Perspective**: Skeptical SME buyer (120-person Singapore company, $15-30K/year HR software budget)

---

## Value Proposition Assessment

### 1. "Unified HR + Recruitment" — STRONG (with caveats)

**Verdict**: This is the strongest value proposition. The hire-to-employee conversion path exists end-to-end in code.

**What works**: When a candidate is hired, an invitation is created, the candidate transitions to "hired" stage, and the onboarding system kicks in. The data models share the same database — no CSV export/import.

**What undermines it**: The hire endpoint does NOT pre-fill employee data from the candidate record. Name, email, phone, NRIC, DOB, nationality, address — all collected during recruitment but not carried forward. The new hire has to re-enter everything. This kills the "seamless conversion" story.

**Fix required**: Candidate-to-employee conversion must pre-fill every shared field. When the employee logs in, their profile should be 80% complete from data already collected.

**Would an SME pay?** Yes, if it actually works. $1,080-$1,800/year in savings from eliminated data re-entry, plus $600-$2,400/year in avoided separate ATS subscription.

### 2. "AI-Powered Screening" — WEAK (risky, commoditized)

**Verdict**: Every ATS vendor claims this. It's a commodity promise, not a differentiator.

**Risk**: AI screening is a regulatory minefield. TAFEP's fair hiring guidelines require merit-based evaluation. If AI screens out candidates based on patterns correlated with race/age/gender/nationality, the company faces investigation.

**What would actually differentiate**: Don't sell "AI screening." Sell **"compliant screening"**:

1. Job ad compliance checker (flag discriminatory language before publishing)
2. Structured scorecard generator (forces merit-based evaluation, creates audit trail)
3. PDPA consent automation (track consent, retention, auto-deletion)

These leverage Arbor's existing TAFEP/FCF knowledge base — something no standalone ATS has.

**Would an SME pay for generic AI screening?** Unlikely — they'll use LinkedIn's free filters. For compliance-integrated screening that protects them from TAFEP complaints? Possibly. A single investigation costs $5,000-$15,000 in legal fees.

### 3. "Compliance Built In" — UNDERAPPRECIATED (strongest long-term differentiator)

**Verdict**: Arbor has a genuine, non-trivial structural advantage. The compliance infrastructure (TAFEP KB, FairEmploymentAgent, PDPA module, compliance checker) is real and deep. No competitor has this for Singapore recruitment.

**Problem**: None of it is currently connected to the recruitment flow. The infrastructure exists in parallel universes.

**Three high-impact compliance features**:

1. **Pre-publish compliance gate**: "This job description mentions 'young and dynamic' — TAFEP guidelines flag age-related language." 3-second interaction prevents 3-month investigation.
2. **Candidate data lifecycle**: Auto-schedule data anonymization per PDPA retention policy. Show HR: "12 candidate records will be anonymized next month."
3. **Fair hiring audit trail**: Log every stage transition, score, and rejection reason — automatically creates TAFEP audit evidence as a byproduct of normal work.

**Would an SME pay?** Not as a standalone feature. But as a differentiator when choosing between Arbor and "Workable + spreadsheet," it tips the scale.

### 4. "One Platform, No Integrations" — CONDITIONAL (threshold-dependent)

**Verdict**: Only works if the recruitment module crosses a minimum viability threshold. Below that, this prop actively hurts you ("they stretched too thin into recruitment").

**Minimum viability threshold**:

- Resume upload and inline viewing (NON-NEGOTIABLE gap)
- Candidate pipeline tracking (exists but buggy)
- Interview scheduling with notifications (basic version exists)
- Candidate search and filter
- Basic metrics (open positions, pipeline counts)

**Current assessment**: 60% of the way to demo-ready, 40% to production-ready. The remaining work is mostly plumbing, not architecture.

---

## Demo Script (What Would Convince a Buyer)

**Minutes 1-5**: Show a live company with 30 employees. "You need to hire an F&B Operations Manager."

**Minutes 5-10**: Create job → system flags "young and energetic" as TAFEP risk → one-click fix → publish to careers page.

**Minutes 10-18**: 3 candidates applied. View resumes inline. AI generates structured scorecard. Schedule interviews. Collect feedback.

**Minutes 18-25 (the "aha" moment)**: Click "Hire" → employee record created with data pre-filled → invitation sent → onboarding assigned → switch to payroll, salary already set from offer.

**Minutes 25-30**: "Rejected candidates' data anonymized in 90 days per PDPA. Every interview score logged for TAFEP audit. You didn't do anything extra — compliance just happened."

---

## Cross-Cutting Issues Found

| Issue                                                                            | Severity          |
| -------------------------------------------------------------------------------- | ----------------- |
| Frontend stage `"new"` vs backend `"applied"` — candidates invisible in pipeline | HIGH              |
| Offer model referenced but never defined — runtime crash                         | HIGH              |
| Job status `"published"` vs `"open"` — badge rendering broken                    | MEDIUM            |
| Layout USP promises ("analytics", "one-click conversion") don't exist in UI      | LOW (credibility) |

---

## Bottom Line

The strongest proposition is: **when you hire someone in Arbor, every system updates automatically — payroll, onboarding, compliance, leave, org chart.** No standalone ATS can match this.

The single highest-impact investment is completing the candidate-to-employee data bridge and adding resume upload. The compliance features (job ad checker, PDPA lifecycle, audit trail) are the long-term premium justifiers.

**Board recommendation**: "60% demo-ready, 40% production-ready. Fund a 4-6 week focused sprint to close gaps, then evaluate customer response before investing in AI screening features."
