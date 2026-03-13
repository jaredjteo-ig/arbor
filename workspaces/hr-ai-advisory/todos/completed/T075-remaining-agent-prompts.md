# T075 — Add Reasoning Scaffolding to FairEmployment, Tax, and WSH Agents

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T064

## What to build

Apply the same scaffolding pattern from T072-T074 to the three remaining specialist agents: `FairEmploymentAgent`, `TaxAgent`, and `WSHAgent`. Each has distinct high-stakes areas where LLM defaults are wrong or outdated.

## FairEmploymentAgent Acceptance Criteria

- [ ] Scaffold: (1) Identify protected characteristic (2) Check if WFL 2025 applies (enacted, effective date) (3) Apply TAFEP guidelines (4) Check FCF/MyCareersFuture obligations if hiring (5) Assess FWA request handling obligations
- [ ] Common mistakes: WFL 2025 now in force — this is no longer "proposed legislation"; TAFEP is not a regulator but findings can lead to MOM enforcement; FCF job portal mandatory for citizen/PR hiring before EP application
- [ ] Integration test: FWA request question answered with correct statutory framework

## TaxAgent Acceptance Criteria

- [ ] Scaffold: (1) Employee type (tax resident / non-resident / expat) (2) Income type (salary, BIK, stock options, commission) (3) Form identify (IR8A, IR21, S45 withholding) (4) Timeline check (IR21 within 1 month of cessation; AIS by 1 March) (5) Rate lookup
- [ ] Common mistakes: IR21 clearance required when foreign employee ceases employment — not optional; BIK valuation at annual value for accommodation; stock options taxed when exercised (not granted); withholding tax on non-residents at 15% on employment income
- [ ] Integration test: foreign employee leaving the company correctly triggers IR21 obligation

## WSHAgent Acceptance Criteria

- [ ] Scaffold: (1) Scope check — WSH Act applies to ALL workplaces (not just construction) (2) Incident classification (dangerous occurrence / work accident / occupational disease) (3) Reporting trigger (accident causing death or hospitalisation > 24h → report within 10 days; dangerous occurrence → immediately) (4) WICA compensation check (5) Risk assessment obligation
- [ ] Common mistakes: WICA insurance is mandatory for manual workers earning < $2,600 or all manual workers regardless of salary; risk assessments are legally required for all workplaces, not just high-risk sectors; near-miss reporting is best practice but not legally required
- [ ] Integration test: workplace injury with hospitalisation correctly states 10-day reporting deadline to MOM
- [ ] Integration test: WICA insurance question correctly identifies mandatory coverage threshold

## Files

- `src/hr_advisory/agents/specialists/fair_employment.py` — rewrite `_generate_system_prompt()`
- `src/hr_advisory/agents/specialists/tax.py` — rewrite `_generate_system_prompt()`
- `src/hr_advisory/agents/specialists/wsh.py` — rewrite `_generate_system_prompt()`

## Reference

11-agent-architecture-analysis.md Section 3.3 (FairEmploymentAgent, TaxAgent, WSHAgent)

## Definition of Done

- [ ] All three agents have structured scaffold prompts
- [ ] WFL 2025 enactment correctly reflected in FairEmployment
- [ ] IR21 and WICA obligations correctly stated in Tax and WSH
- [ ] All common mistakes items covered by integration tests
