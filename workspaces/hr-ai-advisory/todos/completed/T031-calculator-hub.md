# T031 — Calculator Hub and All Calculators (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Backend** (4 new pure-function calculators):

- Notice period calculator (EA s10 statutory minimums, contractual override, salary-in-lieu)
- Overtime calculator (Part IV eligibility, hourly rate, OT multipliers, salary cap)
- Retrenchment benefit calculator (market norms by sector, Tripartite Advisory reference)
- Cost-to-company calculator (CPF + levy + SDL + WICA breakdown)

**React** (7 calculator forms + hub):

- Calculator hub page with grid of 7 calculator cards
- Detail page with dynamic routing to correct calculator
- Reusable ResultPanel and ResultRow components
- CPF, Quota/Levy, Leave, Notice Period, Overtime, Retrenchment, Cost-to-Company forms
- All with SourceCitation badges and "Ask about this" advisory link

**Flutter** (7 calculator forms + hub):

- Calculator hub screen with tappable cards
- Detail screen with form widget routing via switch expression
- 7 client-side logic files for calculations
- 7 form widgets with result display
- Reusable CalculatorResultCard and ResultRow widgets

## Files

- `src/hr_advisory/workflows/calculators/` — 4 new calculator modules + updated **init**.py
- `apps/web/src/app/(dashboard)/calculators/` — hub, detail, 7 calculator elements, config
- `apps/mobile/lib/features/calculators/` — screens, widgets, logic, models
