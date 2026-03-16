# T099 — Implement Escalation Flow

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T036, T046, T070

## What to build

Replace the inert "Connect to Employment Law Specialist" onClick stub with a real escalation flow. When a user clicks it, open an EscalationDialog that captures: situation description, urgency level, and preferred contact method. Submit via the existing emergency escalation API endpoint. Show a confirmation with expected response time. For amber-tier (moderate risk) responses, also add a lighter "Get professional guidance" link that opens the same dialog pre-filled with lower urgency. This closes the trust gap where the platform suggests escalation but offers no real path to it.

## Acceptance Criteria

### EscalationDialog Component

- [ ] New `EscalationDialog` component created as a modal dialog
- [ ] Form fields: situation description (textarea, required, min 20 chars), urgency level (dropdown: urgent/within-24h/general-enquiry), preferred contact (email/phone, with input)
- [ ] Submit button sends POST to the emergency escalation API
- [ ] On success: dialog closes and shows a toast/inline confirmation: "Request received — a specialist will contact you within [timeframe based on urgency]"
- [ ] On error: shows user-friendly error message, form data preserved
- [ ] Dialog is dismissible via close button or Escape key (unless submission is in progress)

### Red-Tier Integration (Emergency)

- [ ] "Connect to Employment Law Specialist" button in SystemMessage now opens EscalationDialog
- [ ] Button passes the current advisory conversation context (last query + response summary) pre-filled into situation description
- [ ] Urgency defaults to "urgent" for red-tier responses

### Amber-Tier Integration (Guidance)

- [ ] A "Get professional guidance" link is added below amber-tier advisory responses
- [ ] Link opens EscalationDialog with urgency defaulting to "within-24h"
- [ ] Link is visually lighter than the red-tier button (text link, not filled button)

### Backend

- [ ] Escalation API endpoint exists and accepts the form data (create if missing)
- [ ] Escalation records stored in database with timestamp, user ID, urgency, description, contact
- [ ] Admin can view escalation requests (integration with existing admin panel or separate list)

## Files

- `apps/web/src/components/advisory/EscalationDialog.tsx` — new component
- `apps/web/src/components/advisory/SystemMessage.tsx` — wire red-tier button, add amber-tier link
- `src/hr_advisory/api/routers/advisory.py` — add or verify escalation endpoint
- `src/hr_advisory/models/advisory.py` (or equivalent) — EscalationRequest model if missing

## Definition of Done

- [ ] Clicking "Connect to Employment Law Specialist" opens EscalationDialog
- [ ] Escalation form submits successfully to backend
- [ ] Confirmation message shown with expected response time
- [ ] Amber-tier "Get professional guidance" link present and functional
- [ ] Escalation records visible in admin panel
