# Red Team Review: Analysis Gap Assessment

**Date**: 2026-03-11
**Documents Reviewed**: All 8 analysis, plan, and user flow documents
**Verdict**: Strong foundation. 14 gaps identified — 4 critical, 4 major, 6 significant. None are showstoppers. All are addressable.

---

## Critical Findings (4)

### C1: Workplace Fairness Act Deferred to Phase 4

The upcoming Workplace Fairness Legislation (expected 2026-2027) may be the single highest-demand advisory topic at launch. SME owners will be scrambling to understand new anti-discrimination obligations. The plan defers this to Phase 4 (Week 21+). This should be Phase 2 at latest — it's a launch differentiator, not an enhancement.

**Fix**: Move Workplace Fairness Act advisory to Phase 2. It's the regulatory equivalent of launching an accounting platform right before a new tax law takes effect.

### C2: No User Flow for Emergency Scenarios

There's no flow for "I think I'm breaking the law right now" or "MOM just called/visited." This is the highest-urgency, highest-value scenario — the moment where an SME owner will pay anything for help. The current flows assume planned, non-urgent interactions.

**Fix**: Add an "Emergency/Urgent" flow with: (1) quick triage of the situation, (2) immediate obligations and deadlines, (3) what NOT to do, (4) when to engage a lawyer immediately. This flow builds the most trust and drives the most conversions.

### C3: Knowledge Base Population Estimate is Low

The architecture decisions document estimates 4-8 weeks to populate the KB across 18 domains and ~140 sub-topics. At that rate, each sub-topic gets 1-2 hours of research, structuring, and validation. For legal content where accuracy is existential, this is aggressive. Realistic estimate: 8-14 weeks with at least one domain expert reviewing output.

**Fix**: Either narrow launch scope (6-8 domains, not 18) or extend Phase 1-2 timeline. The competitive analysis and value audit both agree that launching with wrong content is worse than launching late.

### C4: Consultant Persona (Highest WTP) Has No Multi-Client Support

Persona D (HR consultants) has the highest willingness to pay and the clearest daily use case. But no delivery phase includes multi-client/multi-company support. A consultant managing 20 SME clients needs to switch between company profiles effortlessly. This is a table-stakes feature for this persona.

**Fix**: Add multi-client profile switching to Phase 2 or 3. This persona may represent 30%+ of early revenue.

---

## Major Findings (4)

### M1: "Open to All" vs. Association Distribution Tension

User confirmed: platform is open to everyone, not restricted. But the competitive analysis and value audit heavily recommend association distribution (ASME, SNEF) as the primary go-to-market. These aren't contradictory, but the plan doesn't reconcile them. How does "open to all" coexist with "association bulk licensing" as the revenue model?

**Fix**: Clarify in the plan: open platform with association partnerships for distribution, credibility, and volume pricing. Similar to how LinkedIn is open to all but sells enterprise licenses.

### M2: Singlish/Multilingual Input Not at Launch

The primary persona (SME owners) in Singapore frequently uses Singlish, code-switches between English and Mandarin, and may not use formal English. Multilingual support is deferred to Phase 5. At minimum, the AI must handle Singlish input and Chinese keywords at launch — not as a feature, but as a basic comprehension requirement.

**Fix**: Ensure the LLM configuration handles Singlish naturally (most modern LLMs already do). Don't treat this as a "multilingual feature" — treat it as input robustness. Test with actual Singlish HR queries during QA.

### M3: Employment Hero Missing from Competitive Analysis

Employment Hero (Australian HRIS, expanded to SG, MY, UK, NZ) is arguably the most dangerous near-term competitor. They have: existing SG user base, payroll + HR in one platform, an "Employment Hero AI" feature in beta, and strong VC backing. They could bolt on AI advisory before this platform launches.

**Fix**: Add to competitive analysis. Monitor their AI feature development closely.

### M4: 48-Hour Update SLA Has No Operational Design

Three documents cite a 48-hour SLA for regulatory changes. But there's no operational process design: who monitors MOM/CPF/IRAS announcements? What's the triage process? Who validates updates? What's the tool chain? This is a commitment without a plan.

**Fix**: Design the Regulatory Change Management process in detail during Phase 1. This is infrastructure, not content — it needs to be built before content needs updating.

---

## Significant Findings (6)

### S1: Government Portal Scraping Fragility

The knowledge base relies on publicly available sources. Government websites change layouts, URLs, and content structure without notice. There's no fallback mechanism or monitoring for source availability.

**Fix**: Build source monitoring into the regulatory change pipeline. When a monitored URL returns different structure, alert for manual review.

### S2: "Both from Day One" vs. Phase 3 Templates

User said both advisory and operational toolkit from day one. But templates/document generation is Phase 3 (Week 15). This expectation gap needs to be resolved — either move basic templates to Phase 1, or align expectations.

**Fix**: Include 10-15 essential templates (employment contract, leave policy, termination letter, KET document) in Phase 1. Full template library remains Phase 3.

### S3: No Returning User Flow

All user flows start from first-time onboarding. There's no flow for "I used this 3 months ago and I'm back with a new question" — dashboard, recent history, profile changes since last visit, new regulatory alerts since last login.

**Fix**: Add a returning user flow with: updated compliance snapshot, new alerts since last visit, and "pick up where you left off" context.

### S4: PR Year Missing from CPF Calculator Flow

The foreign worker quota calculator flow is well-designed, but the CPF calculator flow doesn't explicitly capture PR year (1st, 2nd, 3rd+). PR year dramatically affects CPF contribution rates. This is a common error in real payroll — the platform should prevent it.

**Fix**: Add PR year as a required input for any CPF calculation involving PR employees.

### S5: No Platform Abuse Scenarios

No consideration of: users asking the AI to help them circumvent employment laws, users asking about illegal practices (paying below minimum for PWM sectors, avoiding CPF), or adversarial prompt injection.

**Fix**: Add an abuse/misuse section to the architecture decisions. The AI must refuse to assist with non-compliance and should instead explain why the practice is problematic.

### S6: Market Sizing Inconsistency

The competitive analysis estimates SOM at SGD 6.3-12.6M ARR. The value audit estimates SGD 380K-1.9M ARR. This 3-7x disagreement is unreconciled. The difference is in assumed conversion rates and pricing.

**Fix**: Reconcile with a single, defensible set of assumptions. The truth is likely between them — depends heavily on whether PSG listing is achieved and whether association distribution materializes.

---

## Overall Assessment

The analysis is thorough and the plan is sound. The critical findings (C1-C4) should be addressed before moving to the todo phase. The major findings (M1-M4) should be addressed in the plan. The significant findings (S1-S6) can be resolved during implementation.

None of these are reasons to stop. All of them are reasons to sharpen the plan before building.
