# T020 — CPF Contribution Calculator Workflow

## Status: COMPLETED

## What Was Built

### Pure Calculator (`src/hr_advisory/workflows/calculators/cpf_calculator.py`)

Deterministic CPF contribution calculator with:

- `CPFInput` / `CPFResult` frozen dataclasses
- `CPF_RATE_TABLE` — all rates for SC, PR year 1/2/3+, all 5 age bands (25 rate combinations)
- `CPF_ALLOCATION_TABLE` — OA/SA/MA allocation rates by age band
- `calculate_cpf_contributions()` — pure function, no DB calls
- OW ceiling ($6,800/month), AW ceiling ($102,000 - YTD OW)
- Detailed breakdown output (OW/AW separately, rates, ceilings)

### Kailash Workflow (`src/hr_advisory/workflows/calculators/cpf_workflow.py`)

6-node PythonCodeNode pipeline: validate_input → lookup_rates → apply_ceilings → calculate → allocate → summarize

### Key Design Decisions

- Rates embedded as constants (no DB lookup needed for standard calculation)
- Pure function + workflow wrapper pattern — same as T011 classification
- AW ceiling includes current month's capped OW in YTD calculation
- CPF rounding: nearest dollar (Python's `round()`)
- Allocation to OA/SA/MA: MA gets the residual to ensure OA+SA+MA = total

## Verification

49 tests passed (0 failures, 0 skips):

- Rate table coverage (8 tests)
- Basic calculations for all age bands (7 tests)
- PR graduated rates (4 tests)
- OW/AW ceiling tests (6 tests)
- Account allocation tests (3 tests)
- OW+AW combined calculations (2 tests)
- Breakdown output tests (2 tests)
- Edge cases and input validation (7 tests)
- Kailash workflow tests (6 tests)
- CPF Board published examples (4 tests)

## Key Learning

- PythonCodeNode wraps output in `{"result": <value>}` — must access `results["node_id"]["result"]` not `results["node_id"]`

## Files

- `src/hr_advisory/workflows/calculators/__init__.py`
- `src/hr_advisory/workflows/calculators/cpf_calculator.py`
- `src/hr_advisory/workflows/calculators/cpf_workflow.py`
- `tests/integration/test_cpf_calculator.py`
