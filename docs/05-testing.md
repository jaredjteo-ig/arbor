# Test Strategy and Coverage

## Summary

- **Total tests**: 1,089
- **Skipped**: 0
- **Failures**: 0

## Three-Tier Strategy

Tests are organized into three tiers, each with distinct scope and infrastructure requirements.

### Tier 1: Unit Tests (`tests/unit/`)

Fast, isolated tests with no external dependencies. Mock external services where needed.

| Test File                            | Coverage Area                                      |
| ------------------------------------ | -------------------------------------------------- |
| `test_guardrails.py`                 | Query screening, response screening, rate limits   |
| `test_citation_validator.py`         | Citation validation against KB provisions          |
| `test_eatp_lineage.py`               | Trust chain, genesis records, constraint envelopes |
| `test_disclaimers.py`                | Risk-tiered disclaimer generation                  |
| `test_security_validation.py`        | Input sanitisation, email/UEN validation, CORS     |
| `test_settings.py`                   | Settings loading, production safeguards            |
| `test_overtime_calculator.py`        | Overtime pay computation                           |
| `test_notice_period_calculator.py`   | Notice period by tenure                            |
| `test_retrenchment_calculator.py`    | Retrenchment benefit estimation                    |
| `test_cost_to_company_calculator.py` | Cost-to-company breakdown                          |
| `test_tenant_isolation.py`           | Company access validation                          |
| `test_search_router.py`              | Semantic and full-text search logic                |
| `test_compliance_router.py`          | Compliance check, gap analysis                     |
| `test_token_blocklist.py`            | JWT revocation blocklist                           |
| `test_learning_router.py`            | Learning pipeline endpoints                        |

### Tier 2: Integration Tests (`tests/integration/`)

Tests that exercise real Kailash runtime, DataFlow nodes, and agent interactions. Require a running PostgreSQL database.

| Test File                         | Coverage Area                                           |
| --------------------------------- | ------------------------------------------------------- |
| `test_company_user_models.py`     | DataFlow CRUD for company and user models               |
| `test_knowledge_base_models.py`   | DataFlow CRUD for KB models (acts, domains, provisions) |
| `test_kb_pipeline.py`             | KB content loading pipeline                             |
| `test_kb_employment_act.py`       | Employment Act provision loading and queries            |
| `test_kb_tafep.py`                | TAFEP guidelines loading                                |
| `test_kb_foreign_manpower.py`     | Foreign manpower provisions                             |
| `test_kb_cpf.py`                  | CPF provisions                                          |
| `test_kb_remaining_domains.py`    | WSH and tax domain provisions                           |
| `test_employee_classification.py` | Employee type classification workflow                   |
| `test_cpf_calculator.py`          | CPF calculator with real rates                          |
| `test_leave_calculator.py`        | Leave entitlement calculations                          |
| `test_quota_levy_calculator.py`   | Quota and levy calculations                             |
| `test_agent_orchestration.py`     | Orchestrator agent dispatch planning                    |
| `test_specialist_agents.py`       | Specialist agent responses                              |
| `test_agent_team_integration.py`  | Multi-agent coordination                                |
| `test_learning_pipeline.py`       | Feedback, gaps, recommendations, reports                |
| `test_tenant_isolation.py`        | Tenant isolation with real JWT tokens                   |
| `test_stream_trust_lineage.py`    | SSE streaming with trust chain                          |
| `test_auth.py`                    | Auth service (register, login, tokens, blocklist)       |
| `test_nexus_api.py`               | Nexus platform and router integration                   |

### Tier 3: End-to-End Tests (`tests/e2e/`)

Full scenario tests that exercise the complete platform from API request to response. Use real infrastructure.

| Test File                    | Coverage Area                                        |
| ---------------------------- | ---------------------------------------------------- |
| `test_advisory_scenarios.py` | Advisory queries across all domains, safety chain    |
| `test_calculator_flows.py`   | Calculator endpoints with realistic inputs           |
| `test_onboarding_flow.py`    | Full user onboarding: register, profile, first query |

### SDK Tests (`tests/sdk/`)

Tests that validate Kailash SDK patterns and integration:

| Test File               | Coverage Area                     |
| ----------------------- | --------------------------------- |
| `test_sdk_patterns.py`  | Core SDK workflow patterns        |
| `test_scaffolding.py`   | Project scaffolding and structure |
| `test_design_tokens.py` | Design token system               |

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast, no DB needed)
pytest tests/unit/

# Integration tests (requires PostgreSQL)
pytest tests/integration/

# E2E tests (requires full platform running)
pytest tests/e2e/

# With coverage
pytest --cov=src/hr_advisory --cov-report=term-missing
```

## Configuration

Test configuration in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
```

The root `conftest.py` auto-loads `.env` at the start of every pytest session, ensuring environment variables are available without manual setup.

## Testing Principles

1. **Real infrastructure in integration tests** -- Integration and E2E tests use real Kailash runtime, real DataFlow nodes, and real database queries. No mocking of the Kailash SDK.

2. **Unit tests for logic isolation** -- Unit tests mock external dependencies (database, LLM, network) to test business logic in isolation.

3. **Calculator accuracy** -- Calculator tests use 2026 CPF rates and verify against known-correct values for each age band and citizenship status.

4. **Trust chain verification** -- Tests verify that every advisory response includes a complete trust chain with genesis record, attestations, and constraint validation.

5. **Security coverage** -- Dedicated tests for input sanitisation, tenant isolation, token revocation, rate limiting, and auth edge cases.

6. **Learning pipeline coverage** -- Tests cover the full feedback-to-recommendation cycle, including gap detection, recommendation review, and monthly report generation.
