# T010A — Kaizen Agent Architecture: Domain Specialists

## Status: COMPLETED

## What Was Built

7 domain specialist agents (Tier 2), each grounded in KB with constraint envelopes:

| Agent                | Domain                           | Constraint Envelope                     |
| -------------------- | -------------------------------- | --------------------------------------- |
| EmploymentActAgent   | EA provisions, Part IV, leave    | Cannot advise on tax or CPF rates       |
| CPFAgent             | CPF rates, age bands, OW/AW      | Cannot advise on employment law         |
| ForeignManpowerAgent | DRC quotas, levies, COMPASS      | Cannot advise on local employee matters |
| FairEmploymentAgent  | TAFEP, WFL, FWA                  | Cannot make legal determinations        |
| TaxAgent             | IRAS, BIK, withholding           | Cannot advise on employment law         |
| WSHAgent             | WSH Act, sector requirements     | Cannot advise on compensation           |
| ComplianceAgent      | Cross-domain compliance checking | Cannot make legal determinations        |

### Supporting

- **BaseDomainSpecialist** — shared `advise()` method with KB grounding
- **Signatures** — SpecialistSignature + per-domain signatures with intent/guidelines

## Verification

61 passed, 3 skipped (no API key)

## Files

- `src/hr_advisory/agents/specialists/` — 7 agent files + \_base.py + signatures.py + **init**.py
- `tests/integration/test_specialist_agents.py`
