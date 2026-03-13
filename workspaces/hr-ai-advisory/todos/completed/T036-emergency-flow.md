# T036 — Emergency/Urgent Flow (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Backend**:

- 6 emergency response types: TADM claim, workplace injury, wrongful dismissal, MOM inspection, discrimination complaint, data breach
- Each with: immediate obligations (numbered steps with deadlines), documents needed, step-by-step process, when to get help, key provisions
- `get_emergency_response()` and `list_emergency_topics()` helpers

**React**:

- Hub view: 6 emergency topic cards with red left borders, icons, descriptions
- AlertBanner warning about consulting specialists for complex situations
- Detail view with 4 structured sections:
  - Immediate Obligations (numbered steps with deadline badges)
  - Documents to Gather (interactive checklist)
  - Step-by-Step Process (timeline stepper)
  - When to Get Professional Help (warning-styled list)
- Key provisions as SourceCitation badges
- "Connect to Employment Law Specialist" CTA

**Flutter**:

- EmergencyScreen hub with AlertBanner, 6 AppCard items with red borders
- EmergencyDetailScreen with red header card, 4 expandable sections
- Interactive document checklist with progress counter
- Vertical timeline for process steps
- Zero Flutter analysis issues

## Files

- `src/hr_advisory/workflows/emergency_responses.py` — backend emergency response data
- `apps/web/src/app/(dashboard)/emergency/page.tsx` — React emergency page
- `apps/mobile/lib/features/emergency/screens/emergency_screen.dart` — Flutter hub
- `apps/mobile/lib/features/emergency/screens/emergency_detail_screen.dart` — Flutter detail
