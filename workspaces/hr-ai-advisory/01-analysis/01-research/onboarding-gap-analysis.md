# Onboarding Feature — Gap Analysis & Forward Plan

**Date**: 2026-04-07
**Context**: Onboarding feature built (40% of PRD), red teamed against LIA PRD + 12-sheet Excel template

---

## Current State

### What Works

- 6 DataFlow models (Template, Module, Step, Assignment, StepProgress, PreboardingTask)
- 28 API endpoints (template CRUD, assignment, self-service, pre-boarding, HR approval)
- Excel parser reads all 12 sheets
- Employee My Onboarding page (5 step types: content, checklist, upload, policy ack, approval)
- Admin Onboarding tab (upload template, view assignments, assign to employees)
- SG Standard Onboarding template (seeded)

### What's Broken

- Seed script crashes at employee enrichment + payroll
- Employee profiles are empty (no DOB, gender, race, banking, etc.)
- 10 of 12 Excel sheets are parsed then silently discarded
- Onboarding assignments fail (datetime bug — fixed but not deployed/tested)

### What's Missing (vs PRD)

- Pre-boarding automation (emails, IT provisioning, buddy, reminders)
- Conversational onboarding (chat-guided experience)
- Pulse surveys (Day 30/60)
- Milestone tracker (30/60/90 reviews)
- Analytics (completion rates, attrition risk)
- Admin filters (department, cohort, date range)
- Export to CSV/Excel

---

## Strategic Analysis

### The 80/15/5 Rule Applied

**80% Reusable (Platform)**:

- Template/module/step system ✅ (built)
- Assignment + progress tracking ✅ (built)
- Employee self-service step completion ✅ (built)
- Excel template import ✅ (built, needs sheet wiring)
- Pre-boarding task model ✅ (built)
- Policy acknowledgment integration ✅ (built)

**15% Self-Service (Configurable)**:

- Which sheets to parse from Excel → already configurable
- Step types (content/checklist/upload/policy/form/approval) → extensible
- Mandatory vs optional modules → configurable via is_mandatory flag
- Role-specific module filtering → model has role_filter field (unused)
- Due dates and overdue detection → built

**5% Customization**:

- LIA-specific branding → removed ✓
- Company-specific content → injected via Excel upload
- SG compliance steps → seeded in default template

### Value Proposition Critique

**Strong**:

- Excel-first configuration (HR teams understand spreadsheets, not code)
- Singapore compliance built-in (CPF, PDPA, WSH, EA in default template)
- Integrated with existing HRIS (payroll, leave, policies, attendance)
- Policy acknowledgment creates audit-grade records

**Weak**:

- No chat interface (the PRD's primary differentiator is missing)
- No pulse surveys (no early warning for disengagement)
- 10 sheets of carefully structured data get thrown away on import

### What Competitors Do

| Feature                   | BambooHR | Talenox | HReasily | **Central**           |
| ------------------------- | -------- | ------- | -------- | --------------------- |
| Template-based onboarding | Yes      | No      | Basic    | Yes                   |
| Multi-step types          | Partial  | No      | No       | **Yes (6 types)**     |
| Excel import              | Yes      | No      | CSV      | **Yes (12 sheets)**   |
| Policy acknowledgment     | Partial  | No      | No       | **Yes (audit trail)** |
| Chat-guided               | No       | No      | No       | **No (gap)**          |
| Pulse surveys             | Yes      | No      | No       | **No (gap)**          |
| Pre-boarding              | Yes      | No      | No       | **Partial**           |
| SG compliance built-in    | No       | Partial | Partial  | **Yes**               |

---

## Recommended Priority Order

### Phase A: Foundation Fix (Do First — blocks everything)

1. **Fix seed script + re-seed** — get demo data working (employees, profiles, payroll, leave)
2. **Wire remaining 10 Excel sheets** into import (create pre-boarding tasks, link policies, store role configs)
3. **Deploy + verify** onboarding assignment works end-to-end

### Phase B: Core Gaps (High value, moderate effort)

4. **Pre-boarding automation** — auto-create tasks from Sheet 12 on assignment, admin checklist UI
5. **Admin filters + export** — department, status, date filters on onboarding tab, CSV export
6. **Buddy assignment** — use Sheet 11 contacts, display in onboarding UI

### Phase C: Differentiators (High value, significant effort)

7. **Pulse surveys** — new model, Day 30/60 triggers, 5-question NPS, scoring + alerts
8. **Milestone tracker** — 30/60/90 review scheduling from Sheet 9, calendar integration
9. **Onboarding analytics** — completion rates, time-to-complete, department breakdowns

### Phase D: Advanced (Significant effort, future)

10. **Conversational onboarding** — use parsed sheet data as RAG knowledge base, chat-guided experience
11. **IT provisioning workflow** — Sheet 6 data, task assignment to IT role, SLA tracking
12. **Role-specific paths** — Sheet 5 role configs, auto-select modules by designation

---

## Immediate Next Steps

1. Deploy latest code (seed fixes, health endpoint, role endpoint, delete invitation)
2. Re-seed demo data (all employee profiles, payroll, leave, etc.)
3. Wire Sheets 5-12 into the import endpoint
4. Test onboarding end-to-end: upload template → assign → employee completes steps
5. Build pre-boarding task UI
