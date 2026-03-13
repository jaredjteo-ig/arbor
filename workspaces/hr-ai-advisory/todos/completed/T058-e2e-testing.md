# T058 — Comprehensive E2E Testing

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Test Infrastructure**:

- `conftest.py` with `TestConfig` for environment-aware test configuration and `TestUser` fixtures for all 4 personas (SME owner, HR manager, consultant, foreign entrepreneur)

**Advisory Scenario Tests**:

- `test_advisory_scenarios.py` — parameterised tests covering all 14 baseline advisory scenarios across regulatory domains (Employment Act, CPF, foreign manpower, TAFEP, WSH, PDPA)

**Onboarding Flow Tests**:

- `test_onboarding_flow.py` — end-to-end onboarding journey tests for each persona, verifying profile setup, sector detection, and initial advisory routing

**Calculator Accuracy Tests**:

- `test_calculator_flows.py` — CPF contribution accuracy tests, leave entitlement calculation tests, and quota/levy projection tests with known-correct expected values

**Coverage Verification**:

- `TestScenarioCoverage` — meta-tests verifying that all regulatory categories, all 4 personas, and all 3 risk tiers (LOW, MEDIUM, HIGH) are covered by the test suite

## Files

- `tests/e2e/conftest.py` — test configuration and persona fixtures
- `tests/e2e/test_advisory_scenarios.py` — parameterised advisory scenario tests
- `tests/e2e/test_onboarding_flow.py` — onboarding journey tests
- `tests/e2e/test_calculator_flows.py` — calculator accuracy tests
