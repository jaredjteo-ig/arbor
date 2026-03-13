# T084 — QA Sessions Tab in Admin Page (Frontend)

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T083

## What to build

Add a "QA Sessions" tab to the existing React admin panel (T041). The tab shows all QA sessions (active and completed), allows starting a new session with configuration filters, and shows aggregate quality score summaries for completed sessions.

## Acceptance Criteria

- [ ] "QA Sessions" tab added alongside existing admin tabs (Overview, Regulatory Updates, KB Management, Feedback Review, Audit)
- [ ] Session list view shows: reviewer name, date created, date completed (if done), status badge (active/completed), conversation count, average overall score (for completed)
- [ ] Active sessions shown at top of list
- [ ] "Start New Session" button opens a configuration modal with filters:
  - Date range picker (conversations to review)
  - Risk tier filter (all, green, amber, red)
  - Domain filter (all, or specific domain)
  - Flagged only toggle (only conversations with user feedback flags)
  - Confidence range slider (0.0 to 1.0)
  - Sampling strategy selector (random, lowest-confidence, flagged-first, recent-first)
- [ ] Submit starts a session via `POST /admin/qa/sessions` and navigates to the session detail view
- [ ] Session detail view shows session metadata and a list of conversations to review (links to T085 conversation browser)
- [ ] Completed session shows summary scorecard: average per-dimension scores, failure category breakdown
- [ ] All API calls use the existing `apiService` pattern from T013

## Files

- `apps/web/src/components/admin/QASessionsTab.tsx` — new component
- `apps/web/src/components/admin/NewSessionModal.tsx` — new component
- `apps/web/src/components/admin/SessionSummary.tsx` — new component
- `apps/web/src/pages/admin/index.tsx` — add QA Sessions tab

## Reference

12-human-qa-workflow-design.md Section 2.1 (Session Browser)

## Definition of Done

- [ ] Tab visible in admin panel for admin users only
- [ ] New session modal submits to API and creates session
- [ ] Session list paginates (10 per page)
- [ ] Completed session scorecard renders dimension scores as horizontal bar chart
