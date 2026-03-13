# T021 — Foreign Worker Quota & Levy Calculator

## Status: COMPLETED

## What Was Built

### Pure Calculator (`src/hr_advisory/workflows/calculators/quota_levy_calculator.py`)

Deterministic foreign worker quota and levy calculator with:

- `QuotaLevyInput` / `QuotaLevyResult` frozen dataclasses
- `SECTOR_DRC` — DRC limits for 5 sectors (services 35%, manufacturing 60%, construction 87.5%, process 60%, marine 60%)
- `LEVY_RATES` — by (sector, pass_type) with tiered rates
- `calculate_quota_levy()` — pure function, no DB calls
- Current state: ratio, DRC utilisation, sub-quotas (SP/WP), headroom
- Scenario projection: what-if hiring analysis with feasibility check
- Levy calculation: current and projected monthly costs
- Warnings: approaching ceiling (>90%), infeasible scenarios

### Key Design Decisions

- Sub-quotas vary by sector: services has SP sub-DRC (15%), manufacturing has WP sub-DRC (25%)
- EP workers don't count toward DRC but increase the denominator (total workforce)
- Headroom formula: max_foreign = drc_limit \* (local + ep) / (1 - drc_limit)
- Scenario feasibility requires ALL limits to pass (overall DRC + all sub-quotas)
- Case-insensitive sector matching

## Verification

24 tests passed (0 failures, 0 skips):

- Sector DRC tables (3 tests)
- Basic quota calculations (6 tests)
- Sub-quota checks (2 tests)
- What-if scenarios (3 tests)
- Levy calculations (4 tests)
- Headroom calculations (3 tests)
- Edge cases and validation (3 tests)

## Files

- `src/hr_advisory/workflows/calculators/quota_levy_calculator.py`
- `tests/integration/test_quota_levy_calculator.py`
