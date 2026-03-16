# T093 — Reduce and Group Sidebar Navigation

**Status**: ACTIVE
**Milestone**: 10 — Demo-Ready First Impressions
**Priority**: MEDIUM
**Estimated Effort**: 3h
**Dependencies**: T005, T039

## What to build

Restructure the sidebar navigation from 12 flat items into labelled groups that match how users think about their work. The current flat list is cognitively heavy and mixes primary tasks with secondary management items. Move the Alerts notification to the top bar bell icon only (removing it from the sidebar). Move Company Profile into Settings. Target ~9 visible items in 3 clearly labelled groups.

## Acceptance Criteria

### Navigation Groups

- [ ] Three labeled navigation groups implemented:
  - **Core**: Dashboard, Advisory, Compliance
  - **Tools**: Calculators, Documents
  - **Management**: Clients, Analytics
- [ ] Group labels are visually distinct from nav items (smaller, muted text, uppercase)
- [ ] Total visible sidebar items reduced from 12 to ~9

### Removed / Relocated Items

- [ ] "Alerts" removed from sidebar — notification bell in top bar is the only entry point for alerts
- [ ] "Company Profile" removed from sidebar — accessible only via Settings or top bar user menu
- [ ] No broken routes — all removed items are still reachable via their new locations

### Visual Quality

- [ ] Sidebar groups have subtle dividers between them
- [ ] Active state styling works correctly for all grouped items
- [ ] Collapsed sidebar (mobile/narrow) shows icon only, no group labels
- [ ] Keyboard navigation through grouped items works correctly (Tab order follows visual order)

## Files

- `apps/web/src/components/shell/NavigationSidebar.tsx` — restructure navigation items into groups
- `apps/web/src/components/shell/TopBar.tsx` — verify bell icon links to /alerts
- `apps/web/src/app/(dashboard)/alerts/page.tsx` — confirm page still exists and is routed

## Definition of Done

- [ ] Sidebar shows exactly 3 labeled groups (Core, Tools, Management)
- [ ] Total visible items at most 9
- [ ] Alerts and Company Profile removed from sidebar
- [ ] All items remain navigable via their new locations
- [ ] Mobile layout unaffected (icon-only collapsed state)
