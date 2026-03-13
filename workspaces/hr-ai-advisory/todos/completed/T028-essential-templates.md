# T028 — Essential Templates (Phase 1 Bundle)

## Status: COMPLETED

## What Was Built

### 12 EA-Compliant Document Templates

Each template includes: structured content with `{{FIELD_NAME}}` placeholders, required/optional fields list, linked KB provision IDs, and compliance notes.

#### Contracts (3)

1. **Employment Contract (Full-Time)** — Full KET-compliant contract with sections for probation, remuneration, working hours, leave, CPF, termination, confidentiality
2. **Employment Contract (Part-Time)** — Part-time contract with pro-rated entitlements per EA Part-Time Regulations
3. **Key Employment Terms (KET)** — Standalone KET document per EA s95A Fourth Schedule

#### Policies (3)

4. **Annual Leave Policy** — Leave schedule aligned with EA Part X (7-14 days by year of service)
5. **Sick Leave Policy** — MC requirements per EA s89 (14 outpatient + 60 hospitalisation days)
6. **Flexible Work Arrangement Policy** — FWA framework per TG-FWAR guidelines

#### Letters (3)

7. **Termination Letter (With Notice)** — Includes final payment details per EA s22, tax clearance reminder
8. **Resignation Acceptance Letter** — Confirmation of last working day, handover, final settlement
9. **Warning Letter** — Supports 1st/2nd/final warning levels, progressive discipline per TGFEP

#### Forms (3)

10. **FWA Request Form** — Structured request with employer response section per TG-FWAR 2-month response requirement
11. **Expense Claims Form** — Receipt-based reimbursement with approval workflow
12. **Timesheet Template** — Weekly hours tracking with OT limits per EA Part IV (72h/month cap)

### API Integration

Updated `/document/templates` endpoint to serve real templates instead of placeholders:

- `GET /templates` — Lists all 12 templates with metadata (supports `?category=` filter)
- `GET /templates/{id}` — Full template detail including content and linked provisions
- `POST /generate` — Fills template placeholders with provided field values, validates required fields

### Template Infrastructure

- `TemplateDefinition` frozen dataclass with: name, type, category, description, content, required_fields, optional_fields, linked_provisions, compliance_notes
- `get_template_by_type()` helper for filtering by contract/policy/letter/form/ket

## Verification

`python -c "from hr_advisory.templates.content import TEMPLATES; print(len(TEMPLATES))"` → 12

## Files

- `src/hr_advisory/templates/__init__.py`
- `src/hr_advisory/templates/content.py` (12 template definitions)
- `src/hr_advisory/api/routers/document.py` (updated from placeholder to real templates)
