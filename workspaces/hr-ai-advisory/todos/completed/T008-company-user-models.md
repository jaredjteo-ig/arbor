# T008 — DataFlow Models: Company and User

## Status: COMPLETED

## What Was Built

6 DataFlow models for the transactional layer:

| Model           | Purpose                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------- |
| Company         | SME profile with workforce composition (5 headcount types), UEN, sector, salary ranges                        |
| User            | Platform users with email, role (owner/hr_manager/consultant), preferences (JSON)                             |
| Conversation    | Thread grouping advisory sessions per user + company                                                          |
| AdvisorySession | Full audit trail: query, response, provisions cited, agents involved, trust lineage, genesis record, feedback |
| ContentUpdate   | Regulatory change tracking with urgency and affected domains                                                  |
| Template        | Reusable document templates linked to provisions                                                              |

## Key Design Decisions

- Company has `multi_tenant: True` for consultant mode (red team fix C4)
- `template_version` (not `version`) to avoid collision with Kailash node metadata field
- AdvisorySession stores full EATP trust lineage and COC genesis record as JSON
- All JSON fields use `Optional[dict]` for DataFlow compatibility
- Float comparisons use tolerance (DataFlow returns slightly different float precision)

## Verification

9 tests passing:

- Model registration (1), Company CRUD with headcounts (2), User CRUD (2)
- Full advisory flow: company → user → conversation → session (1)
- Feedback on session (1), Content update (1), Template (1)

All 37 integration tests pass across T007 + T008.

## Files

- `src/hr_advisory/models/company_user.py`
- `src/hr_advisory/models/__init__.py` (updated)
- `tests/integration/test_company_user_models.py`
