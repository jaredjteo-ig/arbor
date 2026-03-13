# T073 — Add Reasoning Scaffolding to CPFAgent

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 2h
**Dependencies**: T064

## What to build

Add CPF-specific reasoning scaffolding and common mistakes to `CPFAgent`'s system prompt. CPF is highly structured (contribution rates, ceilings, age bands, residency status) and errors arise from conflating categories. The scaffold and mistakes section must make these distinctions explicit and enforce lookup-before-answer behaviour.

## Acceptance Criteria

- [ ] System prompt includes reasoning scaffold: (1) Residency status — SC/PR/foreigner? (2) Age band — which CPF age bracket? (3) OW vs AW — identify wage type (4) Ceiling check — is OW above $6,000 cap or AW above Annual Wage Ceiling? (5) Rate lookup — employer rate + employee rate from correct table
- [ ] Common Mistakes section includes:
  - Foreigners do not contribute to CPF (only SDL and FWL apply)
  - PR rates are graduated in Years 1 and 2 (lower than SC rates)
  - Ordinary Wage ceiling is $6,000/month (contributions on OW capped here)
  - Annual Wage Ceiling is $102,000/year (total OW + AW contribution base)
  - Late payment interest: 18% per annum (1.5% per month), minimum $5
  - CPF for part-timers: same rates if they are SC/PR (no exemption for part-time)
  - SDL is payable on all employees' wages up to $4,500
- [ ] Reasoning scaffold leads to explicit rate citation before giving any number
- [ ] Integration test: CPF for 35-year-old SC employee at $5,500/month answered correctly
- [ ] Integration test: CPF for Year 1 PR at same salary gives lower (graduated) rate
- [ ] Integration test: foreigner employee CPF query correctly states no CPF, mentions SDL

## Files

- `src/hr_advisory/agents/specialists/cpf.py` — rewrite `_generate_system_prompt()`

## Reference

11-agent-architecture-analysis.md Section 3.3 CPFAgent

## Definition of Done

- [ ] SC vs PR vs foreigner distinction tested
- [ ] OW ceiling and AW ceiling correctly applied
- [ ] Late payment interest correctly stated
