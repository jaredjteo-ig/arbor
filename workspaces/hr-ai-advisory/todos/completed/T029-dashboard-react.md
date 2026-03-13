# T029 — Dashboard (Returning User, React Web)

## Status: COMPLETED

## What Was Built

### Returning User Dashboard

1. **Personalised greeting** — "Welcome back, {firstName}" with subtitle
2. **Regulatory alert banner** — Dismissible AlertBanner for urgent regulatory changes (KET update example)
3. **Metric cards** — 3-column grid: Compliance Score (78/100), Pending Actions (3), Next Deadline (31 Mar CPF)
4. **Quick actions** — 4-button grid: Ask a question (primary CTA), Run a calculation, Generate a document, Compliance check
5. **Recent conversations** — 3 recent advisory chats with topic, date, risk-tier badge, click to resume
6. **Pending action items** — Checklist with risk badges, due dates, "Run Compliance Check" CTA

### Layout

- Max-width 4xl container with responsive grid
- Metric cards: 1-col mobile → 3-col desktop
- Quick actions: 2-col mobile → 4-col desktop
- Recent + Pending: 1-col mobile → 2-col desktop (lg breakpoint)

### Data

Currently using placeholder data that demonstrates realistic Singapore HR content. In production, data comes from API hooks (useCompliance, useAdvisoryHistory, useAlerts).

## Verification

TypeScript compiles clean (0 errors).

## Files

- `apps/web/src/app/(dashboard)/page.tsx` (replaced placeholder)
