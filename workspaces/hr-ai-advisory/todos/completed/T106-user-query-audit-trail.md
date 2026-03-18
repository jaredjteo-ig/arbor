# T106 — Add User Query Audit Trail

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: MEDIUM
**Estimated Effort**: 6h
**Dependencies**: T026, T065, T044

## What to build

Create an "Advisory History" page accessible to all authenticated users showing their query log: a searchable, filterable list of every advisory interaction with date/time, query text, response summary, risk tier, provisions cited, and confidence score. Make the log exportable as CSV and PDF. This is a compliance and accountability feature — HR Directors need a record of what they asked and what guidance they received to defend decisions if audited.

## Acceptance Criteria

### Advisory History Page

- [ ] New page at `/advisory/history` accessible from the Advisory sidebar section or from ConversationSidebar
- [ ] Lists all conversations for the authenticated user in reverse chronological order (newest first)
- [ ] Each row shows: date/time, first message (query preview, truncated), risk tier badge, provisions cited count, confidence level, conversation length (turns)
- [ ] Clicking a row navigates to or loads that conversation in the advisory chat

### Search and Filter

- [ ] Full-text search across query text (client-side or server-side)
- [ ] Filter by risk tier (green/amber/red)
- [ ] Filter by date range (from/to date pickers)
- [ ] Filter by domain (Employment Act, CPF, Foreign Manpower, etc.)
- [ ] Filters and search can be combined

### Export

- [ ] "Export CSV" button downloads a CSV file with columns: date, time, query, risk_tier, provisions_cited, confidence_score, conversation_id
- [ ] "Export PDF" button generates a formatted PDF report with the Arbor logo, the filtered/searched result set, and a disclaimer footer
- [ ] Export respects current filters (exports what is currently visible)
- [ ] Export limited to the current user's data (enforced server-side)

### Backend

- [ ] If no history list endpoint exists, add `GET /advisory/history` that returns conversations with summary fields for the authenticated user
- [ ] Endpoint supports query params: `search`, `risk_tier`, `domain`, `date_from`, `date_to`, `page`, `limit`
- [ ] Response includes all fields needed by the frontend (date, query preview, risk_tier, provisions_cited, confidence)

## Files

- `apps/web/src/app/(dashboard)/advisory/history/page.tsx` — new page
- `apps/web/src/components/advisory/HistoryTable.tsx` — new component
- `apps/web/src/components/advisory/HistoryExportButtons.tsx` — new component
- `src/hr_advisory/api/routers/advisory.py` — add history list endpoint with filters if missing

## Definition of Done

- [ ] Advisory History page loads and shows real conversation data for the current user
- [ ] Search and all filters work correctly
- [ ] CSV export downloads with correct columns and data
- [ ] PDF export generates correctly formatted document
- [ ] Non-authenticated access returns 401
