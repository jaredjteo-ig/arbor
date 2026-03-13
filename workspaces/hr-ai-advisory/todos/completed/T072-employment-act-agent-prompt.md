# T072 — Add Reasoning Scaffolding to EmploymentActAgent

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T064

## What to build

Replace the `EmploymentActAgent`'s generic system prompt with a structured 5-step reasoning scaffold and explicit common-mistakes section. The scaffold forces the agent to reason in order: (1) Applicability — does EA apply, and which part? (2) Provisions — which specific sections govern? (3) Application — how do the sections apply to this company's facts? (4) Risk — what are the consequences of non-compliance? (5) Cross-domain — does this interact with CPF, EFMA, or other domains? The common mistakes section lists the specific errors the current system makes.

## Acceptance Criteria

- [ ] System prompt includes 5-step reasoning scaffold (labeled STEP 1 through STEP 5)
- [ ] Common Mistakes section includes at minimum:
  - Part IV coverage threshold: manual workers covered regardless of salary up to $4,500; non-manual workers covered up to $2,600 for rest day/OT
  - Notice period default is 1 day for service < 26 weeks — not "one month"
  - Dismissal inquiry is required for employees with service > 12 months — not optional
  - Salary deductions capped at 25% of wages per period under s.27
  - Retrenchment benefit is NOT statutory — contractual or negotiated only
  - EA does NOT cover domestic workers or seafarers
- [ ] Few-shot example included in prompt for a Part IV application question
- [ ] Prompt structured with clear section headers (not a wall of text)
- [ ] Integration test: Part IV coverage question for $2,400/month manual worker answered correctly
- [ ] Integration test: dismissal inquiry requirement correctly stated for 2-year employee

## Files

- `src/hr_advisory/agents/specialists/employment_act.py` — rewrite `_generate_system_prompt()`

## Reference

11-agent-architecture-analysis.md Section 3.3 EmploymentActAgent

## Definition of Done

- [ ] All 6 common mistakes items tested and correct
- [ ] Prompt structured so additions are easy (section-based, not monolithic)
- [ ] Response length for typical query is 300-500 words (not truncated, not padded)
