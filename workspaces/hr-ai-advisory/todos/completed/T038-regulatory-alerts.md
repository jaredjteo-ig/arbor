# T038 — Regulatory Alerts System (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**React** (938 lines):

- Alert list with 8 Singapore regulatory change demo entries (PWM, CPF rates, TG-FWAR, WICA, PDPA, levy rates, TAFEP, EA amendments)
- Three filter tabs: All / Affecting Your Company / Upcoming Changes
- Severity and status filters
- Summary pills: unread count, critical count, this month count
- Expandable alert detail with: impact summary, action items, effective date, CTAs
- Calendar view toggle showing alerts on effective dates
- Mark as read / dismiss functionality

**Flutter** (1026 lines):

- Matching alert screen with 8 demo entries
- ChoiceChip category and severity filters
- Unread count banner
- Alert cards with severity-colored left borders, unread indicators
- Expandable detail with impact summary, actions, effective date
- AppButton CTAs and mark-as-read functionality

## Files

- `apps/web/src/app/(dashboard)/alerts/page.tsx` — React alerts page
- `apps/mobile/lib/features/alerts/screens/alerts_screen.dart` — Flutter alerts screen
