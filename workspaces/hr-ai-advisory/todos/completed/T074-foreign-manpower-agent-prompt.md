# T074 — Add Reasoning Scaffolding to ForeignManpowerAgent

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 2h
**Dependencies**: T064

## What to build

Add EFMA-specific reasoning scaffolding and a common mistakes section to `ForeignManpowerAgent`. Foreign manpower rules (EP, S Pass, WP) have distinct qualification criteria, quota/levy structures, and COMPASS scoring requirements. Conflating pass types or sector differences leads to non-compliance advice.

## Acceptance Criteria

- [ ] System prompt includes reasoning scaffold: (1) Pass type classification (EP/S Pass/WP/Dependent's Pass/LTVP) (2) Sector identification (construction, marine, process, services, manufacturing) (3) Quota check (sector-specific quota ratios) (4) COMPASS assessment (for EP: points-based from Sep 2023) (5) Levy computation (worker category and sector)
- [ ] Common Mistakes section includes:
  - DRC (Dependency Ratio Ceiling) rates differ by sector — do not use a single generic rate
  - COMPASS applies to EP applications from Sep 2023 — not quota-based
  - EP holders are NOT covered by Part IV of Employment Act (they earn above $4,500 threshold)
  - S Pass and WP holders ARE covered by Part IV of Employment Act
  - Levy is NOT deductible from worker's salary — employer's cost only
  - Employer must NOT retain foreign worker's passport — criminal offence under EFMA s.22A
  - Medical insurance: minimum $60,000 inpatient per year for S Pass and WP
  - Security bond: $5,000 per WP worker
- [ ] Integration test: EP application question correctly explains COMPASS, not quota
- [ ] Integration test: question about deducting levy from salary correctly refused
- [ ] Integration test: passport retention question answered as criminal offence

## Files

- `src/hr_advisory/agents/specialists/foreign_manpower.py` — rewrite `_generate_system_prompt()`

## Reference

11-agent-architecture-analysis.md Section 3.3 ForeignManpowerAgent

## Definition of Done

- [ ] All 8 common mistakes items tested
- [ ] COMPASS vs DRC distinction correctly applied
- [ ] Part IV coverage difference between pass types correctly stated
