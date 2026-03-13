# T049 — Accuracy Testing

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Test Framework Data Models**:

- `ScenarioCategory` enum (EMPLOYMENT_ACT, CPF, FOREIGN_MANPOWER, FAIR_EMPLOYMENT, WSH, TAX, CROSS_DOMAIN)
- `TestScenario` frozen dataclass with query, expected domains, expected provisions, expected risk tier, key facts (must appear), and anti-facts (hallucination detection)
- `AccuracyResult` dataclass tracking pass/fail, domain match, provision match, risk tier match, key facts coverage, hallucinations detected, and confidence score

**14 Baseline Scenarios Across 4 Personas**:

- Persona A (new employer): 5 scenarios — first hire documents (KET/payslip), CPF registration, annual leave entitlement, resignation notice periods, payslip requirements
- Persona B (growing SME): 5 scenarios — misconduct dismissal (amber), overtime calculation, foreign worker permits, workplace injury (red), retrenchment (red)
- Persona C (consultant): 2 scenarios — company growth compliance thresholds (cross-domain), TAFEP complaint handling (red)
- Persona D (employee): 2 scenarios — missing KET compliance, dismissal during maternity leave (red)

**Anti-Fact Hallucination Detection**:

- Scenarios include anti-facts that must NOT appear in responses (e.g., "can immediately fire without process" for misconduct dismissal, "14 days minimum" for annual leave, "employer is free to dismiss" for maternity dismissal)

**Scenario Access**:

- `get_scenario()` — retrieve a specific scenario by ID
- `list_scenarios()` — list scenarios with optional category and persona filters

## Files

- `src/hr_advisory/trust/accuracy_testing.py` — accuracy testing framework module
