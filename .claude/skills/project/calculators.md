---
name: calculators
description: "HR calculator implementation patterns. Use when working on CPF, leave, salary, quota/levy, overtime, notice period, or retrenchment calculators."
---

# HR Calculators

All calculators use Kailash Core SDK workflows in `src/hr_advisory/workflows/calculators/`.

## Calculator Index

| Calculator   | Endpoint                        | Key Input                        | Key Output                      |
| ------------ | ------------------------------- | -------------------------------- | ------------------------------- |
| CPF          | `POST /calculator/cpf`          | salary, age, citizenship         | employer/employee contributions |
| Leave        | `POST /calculator/leave`        | years_of_service, leave_type     | days_entitled                   |
| Salary       | `POST /calculator/salary`       | salary, age, citizenship, sector | net pay, total cost             |
| Quota/Levy   | `POST /calculator/quota`        | sector, headcount                | quota ceiling, levy amount      |
| Overtime     | `POST /calculator/overtime`     | salary, hours                    | overtime pay                    |
| Notice       | `POST /calculator/notice`       | tenure                           | notice period                   |
| Retrenchment | `POST /calculator/retrenchment` | salary, years                    | estimated benefit               |

## CPF 2026 Rates (Singapore Citizens)

| Age    | Employer | Employee | Total |
| ------ | -------- | -------- | ----- |
| <=55   | 17%      | 20%      | 37%   |
| >55-60 | 14.5%    | 15%      | 29.5% |
| >60-65 | 11%      | 9.5%     | 20.5% |
| >65-70 | 8.5%     | 7%       | 15.5% |
| >70    | 7.5%     | 5%       | 12.5% |

**Ceilings**: OW $8,000/month (raised from $7,400 on 1 Jan 2026), AW $102,000 - cumulative OW

**PR graduated rates**: Year 1 (lower), Year 2 (medium), Year 3+ (full SC rates)

## Leave Entitlements (EA Part IV)

**Annual**: 7 days (yr 1) → 14 days (yr 8+), +1 day per year

**Sick**: 14 days outpatient, 60 days hospitalisation (inclusive)

**Maternity**: 16 weeks | **Paternity**: 4 weeks | **Childcare**: 6 days (<7yo)

## Implementation Pattern

```python
from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

def calculate_cpf(salary: float, age: int, citizenship: str = "SC") -> dict:
    wf = WorkflowBuilder()
    wf.add_node("PythonCodeNode", "calc", {
        "code": CPF_CALCULATION_CODE,
        "inputs": {"salary": salary, "age": age, "citizenship": citizenship}
    })
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results["calc"]
```

## Critical Rules

- Rates MUST reflect 2026 legislation
- Use named constants, not inline numbers
- Enforce OW/AW ceilings
- Handle edge cases: zero salary, boundary ages, PR transitions
- Tests MUST verify against known-correct values
- The `code` parameter of PythonCodeNode executes arbitrary Python — NEVER interpolate user input into the code string. All user data must be passed via the `inputs` dictionary.

## Key Files

- `src/hr_advisory/workflows/calculators/` — Implementations
- `src/hr_advisory/api/routers/calculator.py` — API endpoints
- `tests/integration/test_cpf_calculator.py` — CPF tests
- `tests/integration/test_leave_calculator.py` — Leave tests
- `tests/e2e/test_calculator_flows.py` — E2E tests

## Related Documentation

- `docs/02-api-reference.md` — Calculator API endpoints
- `docs/01-architecture.md` — Calculator architecture

## Consult Agent

For calculator work: `hr-calculator-specialist`
