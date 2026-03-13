# T030 — Dashboard (Returning User, Flutter Mobile)

## Status: COMPLETED

## What Was Built

### Returning User Dashboard (Flutter)

1. **Personalised greeting** — "Welcome back, {firstName}" from auth state
2. **Notification badge** — AppBar bell icon with badge count, links to alerts
3. **Regulatory alert banner** — Dismissible AlertBanner (warning variant) for KET update
4. **Metric cards** — Horizontal scrollable: Compliance Score, Pending Actions, Next Deadline
5. **Quick actions** — 2x2 grid: Ask a question (primary), Calculate, Documents, Compliance
6. **Recent conversations** — 3 conversation tiles with topic, date, RiskTierBadge, tap to resume
7. **Pending action items** — Risk-tier badge + title + due date per item
8. **Compliance check CTA** — Full-width outlined AppButton at bottom
9. **Pull-to-refresh** — PullToRefresh wrapper for dashboard data

### Mobile Optimizations

- Horizontal scroll for metric cards (fits 2 on screen)
- Quick actions as 2x2 grid (compact for thumb reach)
- Recent conversations as vertical list (no horizontal scroll)
- Pull-to-refresh for data reload

## Verification

`flutter analyze` — 0 issues found.

## Files

- `apps/mobile/lib/features/advisory/screens/home_screen.dart` (replaced placeholder)
