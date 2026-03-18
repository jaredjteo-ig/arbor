---
name: document-generation
description: "Document template and generation patterns. Use when working on document templates, generation endpoints, download, preview, or document history."
---

# Document Generation

HR document templates and generation for Singapore employment contexts.

## Template Categories

The platform provides 12+ templates covering:

- Key Employment Terms (KETs) — mandatory under EA
- Employment contracts
- Company policies (leave, flexible work, etc.)
- IR8A/IR21 tax filing documents
- Termination/retrenchment notices
- Warning letters and performance improvement plans

## API Endpoints

| Endpoint                   | Method | Purpose                                                   | Auth         |
| -------------------------- | ------ | --------------------------------------------------------- | ------------ |
| `/document/templates`      | GET    | List templates (optional `?category=` filter)             | Yes          |
| `/document/templates/{id}` | GET    | Get template with content and linked provisions           | Yes          |
| `/document/preview`        | POST   | Preview with partial fields (shows unfilled placeholders) | Yes          |
| `/document/generate`       | POST   | Generate customised document (returns document_id)        | Yes          |
| `/document/download/{id}`  | GET    | Download generated document                               | Yes + tenant |
| `/document/history`        | GET    | List generated documents (optional `?company_id=`)        | Yes + tenant |

## Security

- All endpoints require authentication
- Download validates tenant isolation (`validate_company_access()`)
- History auto-scopes non-admin users to their own company
- `platform_admin` can view all companies' documents

## Template Structure

Each template includes:

- `template_id`, `name`, `category`
- `content` — Template text with `{{placeholder}}` markers
- `required_fields` — Fields that must be provided
- `optional_fields` — Fields with defaults
- `linked_provisions` — KB provisions referenced by the template

## Generation Flow

```
Client: POST /document/generate
  { "template_id": 1, "company_id": 1, "fields": { "employee_name": "..." } }
    |
    v
Validate required fields → Fill template → Store document → Return document_id
    |
    v
Client: GET /document/download/{document_id}
  → Returns generated document as plain text
```

## Key Files

- `src/hr_advisory/templates/` — Template definitions
- `src/hr_advisory/api/routers/document.py` — Document endpoints
- `docs/02-api-reference.md` — Full API documentation

## Consult Agent

For document work: `arbor-platform-specialist`
