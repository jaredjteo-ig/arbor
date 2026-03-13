# T022 — Leave Entitlement Calculator

## Status: COMPLETED

## What Was Built

### Pure Calculator (`src/hr_advisory/workflows/calculators/leave_calculator.py`)

Deterministic leave entitlement calculator covering all 8 Singapore statutory leave types:

- `LeaveInput` / `LeaveResult` frozen dataclasses
- `LEAVE_CALCULATORS` dispatcher dict — maps leave_type to calculator function
- `calculate_leave_entitlement()` — pure function, no DB calls

### Leave Types Implemented

1. **Annual leave** (EA S88A): 7 days year 1, +1/year, max 14. Pro-rated for partial years. 3-month minimum.
2. **Sick leave** (EA S89): 14 outpatient + 60 hospitalisation (after 6 months). Pro-rated for 3-5 months.
3. **Maternity leave** (EA Part IX + CDCSA): 16 weeks (SC child) or 8 weeks (non-SC). Split/government-paid.
4. **Paternity leave** (CDCSA): 2 weeks government-paid. SC/PR father + SC child required.
5. **Childcare leave** (CDCSA): 6 days/year (SC child under 7) or 2 days (non-SC child).
6. **Infant care leave** (CDCSA): 6 days/year for child under 2.
7. **Shared parental leave** (CDCSA): 4 weeks from mother's maternity. Government-paid.
8. **Adoption leave** (CDCSA): 12 weeks for SC child. Split employer/government-paid.

### Key Design Decisions

- Each leave type has its own calculator function for clarity
- Dispatcher pattern via `LEAVE_CALCULATORS` dict — same as workflow node pattern
- `who_pays` field distinguishes employer/government/split funding
- `government_claim_cap` captures per-period caps where applicable
- Child order (1st/2nd/3rd+) affects maternity funding source
- Pro-ration uses nearest half-day rounding for annual leave

## Verification

28 tests passed (0 failures, 0 skips):

- Annual leave (8 tests): <3mo, pro-rated, years 1-8, max cap, who_pays
- Sick leave (3 tests): <3mo, 3mo pro-rated, 6mo full
- Maternity leave (4 tests): SC child 16wk, non-SC 8wk, 3rd child govt, <3mo
- Paternity leave (3 tests): SC father+child, foreigner, non-SC child
- Childcare leave (4 tests): SC parent+child, no eligible children, non-SC child, foreigner
- Infant care leave (2 tests): infant under 2, no infants
- Shared parental leave (1 test): SC father+child
- Adoption leave (2 tests): SC child, non-SC child
- Invalid leave type (1 test): raises ValueError

## Files

- `src/hr_advisory/workflows/calculators/leave_calculator.py`
- `tests/integration/test_leave_calculator.py`
