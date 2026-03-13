# T052 — Growth-Stage Triggers

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Trigger Taxonomy**:

- `TriggerCategory` enum (HEADCOUNT, FOREIGN_WORKER, COMPLIANCE)
- `TriggerPriority` enum (HIGH, MEDIUM, LOW)

**Data Models**:

- `TriggerAlert` frozen dataclass with trigger ID, category, priority, title, summary, details, relevant provisions, suggested actions, and advisory query (a suggested question to ask the advisor)
- `CompanyProfile` frozen dataclass for trigger evaluation — employee count, previous employee count (for threshold crossing detection), foreign worker and EP holder flags/counts, sector

**7 Growth Triggers**:

- **GROWTH-5** (LOW) — 5+ employees: basic documentation checkpoint — KETs, payslips, CPF setup
- **GROWTH-10** (MEDIUM) — 10+ employees: WSH policy required (Section 12), AIS submission to IRAS, enhanced record-keeping (2-year retention)
- **GROWTH-25** (MEDIUM) — 25+ employees: increased TAFEP scrutiny, FCF MyCareersFuture advertising for EP applications, retrenchment notification (5+ in 6 months)
- **GROWTH-50** (HIGH) — 50+ employees: WSH Officer requirement for certain sectors, enhanced MOM reporting, employee handbook formalisation
- **GROWTH-100** (HIGH) — 100+ employees: enterprise compliance expectations, formal grievance handling, IHRP-certified HR professional recommended, PDPA compliance review
- **GROWTH-FIRST-FW** (HIGH) — first foreign worker: work permit before employment, DRC quota limits, monthly levy, housing/insurance/passport obligations
- **GROWTH-FIRST-EP** (MEDIUM) — first EP holder: COMPASS framework, FCF advertising on MyCareersFuture, minimum $5,000 salary, Part IV exemption, CPF only for PRs

**Threshold Crossing Detection**:

- `_crossed_threshold()` helper compares `employee_count` against `previous_employee_count` to detect upward crossing — prevents re-firing on subsequent evaluations

**Public API**:

- `evaluate_triggers()` — evaluates all triggers against a company profile, returns newly-fired alerts only; each trigger fires once per company (idempotent via per-company fired set)
- `get_fired_triggers()` — returns list of trigger IDs already fired for a company
- `reset_triggers()` — clears fired triggers for a company (for testing)
- `get_all_trigger_ids()` — returns all 7 registered trigger IDs
- `get_trigger_alert()` — retrieves a specific trigger alert by ID for preview/documentation

## Files

- `src/hr_advisory/workflows/growth_triggers.py` — growth-stage triggers module
