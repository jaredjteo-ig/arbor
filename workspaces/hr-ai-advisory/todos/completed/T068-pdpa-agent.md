# T068 — Create PDPAAgent Specialist

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T063, T064

## What to build

No PDPA specialist exists despite PDPA provisions being in the KB and PDPA queries appearing in emergency response handling. Create `PDPAAgent` extending `BaseDomainSpecialist` with `domain="pdpa"`. Cover the core obligations: consent for employee data collection, breach notification (3-day MAS/PDPC deadline), DPO appointment requirements (for organisations above threshold), cross-border data transfer obligations, and employee data access/correction rights.

## Acceptance Criteria

- [ ] `PDPAAgent` class created, extends `BaseDomainSpecialist`
- [ ] System prompt covers: consent obligations, purpose limitation, data breach notification (72-hour for prescribed breaches, 3-day calendar day), DPO requirements, cross-border transfer adequacy, employee data rights
- [ ] Common mistakes section: treating employee consent as freely given, missing breach notification deadline, storing data longer than necessary
- [ ] `domain = "pdpa"` in class definition
- [ ] Added to domain mapping in `dispatch_router.py` (T063)
- [ ] Added to specialist registry in `__init__.py`
- [ ] KB provisions for PDPA domain used via T064 mechanism
- [ ] Integration test: PDPA query routed to PDPAAgent and response cites PDPA 2012 provisions

## Files

- `src/hr_advisory/agents/specialists/pdpa.py` — new file
- `src/hr_advisory/agents/specialists/__init__.py` — add PDPAAgent export
- `src/hr_advisory/agents/orchestration/dispatch_router.py` — add pdpa domain mapping

## Reference

10-adversarial-scenarios.md Category 8 (Privacy and Data scenarios)

## Definition of Done

- [ ] PDPA query correctly routes to PDPAAgent (not FairEmploymentAgent or generic)
- [ ] Response cites PDPA 2012 sections, not generic data privacy concepts
- [ ] Breach notification scenario correctly states 3 calendar days for prescribed breaches
- [ ] DPO requirement threshold correctly applied
