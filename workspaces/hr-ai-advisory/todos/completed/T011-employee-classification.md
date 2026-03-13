# T011 — Core SDK Employee Classification Workflow

## Status: COMPLETED

## What Was Built

Deterministic employee classification engine — 100% pure business logic, no LLM involvement.

### Classification Rules

| Rule               | Logic                                                                        |
| ------------------ | ---------------------------------------------------------------------------- |
| EA Coverage        | All employees except domestic workers, seafarers, government                 |
| Part IV            | Workmen ≤$4,500; non-workman non-executives ≤$2,600; managers excluded       |
| CPF Status         | SC: full; PR: graduated by year (1/2/3+); Foreigners: none                  |
| CPF Age Bands      | ≤55, 55-60, 60-65, 65-70, >70                                               |
| Pass Validation    | EP min $5,000; SP min $3,150; WP no minimum                                 |
| Leave Entitlements | Annual, sick, maternity, paternity, childcare, shared parental, adoption etc |

### Architecture

7-node Kailash Core SDK workflow pipeline:
```
validate_input → classify_ea → classify_part_iv → classify_cpf → validate_pass → determine_leave → summarize
```

Pure functions in `rules.py` independently testable. Workflow wraps them via `PythonCodeNode`.

## Verification

73 tests passed (0 failures, 0 skips):
- 46 pure rule unit tests (Tier 1)
- 27 full workflow integration tests (Tier 2, real LocalRuntime)

## Files

- `src/hr_advisory/workflows/classification/rules.py`
- `src/hr_advisory/workflows/classification/data_classes.py`
- `src/hr_advisory/workflows/classification/employee_classifier.py`
- `src/hr_advisory/workflows/classification/__init__.py`
- `src/hr_advisory/workflows/__init__.py` (updated)
- `tests/integration/test_employee_classification.py`
