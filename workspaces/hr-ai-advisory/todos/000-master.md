# HR AI Advisory — Master Todo Index

**Project**: HR AI Advisory Platform (Singapore SME HR compliance)
**Last Updated**: 2026-03-17
**Total Tasks**: 140 across 15 milestones
**Status**: T001-T108 complete. T109-T140 active (Shadow Agent Evolution — Milestones 13-15).

---

## How to Read This Index

- T001-T108 are **done** — completion records are in `completed/`
- T109-T140 are **active** — detailed files are in `active/`
- Implement M13 first (command surface) — M14 follows — M15 requires both

---

## Milestones 1-12: COMPLETE

T001-T108 across 12 milestones. See `completed/` for details. Covers:

- Full-stack platform (Python + React + Flutter)
- 6 regulatory domains, 33+ provisions, 7 calculators
- 14-step advisory safety chain with SSE streaming
- EATP trust lineage, CARE governance, learning pipeline
- Production deployment at aite.kailash.ai
- 7 red team rounds, 1195+ tests

---

## Milestone 13: Shadow Agent Foundation (Sprint 1)

**Goal**: Replace the floating chat drawer with a command palette and shadow widget. Users can ask questions, run calculations, and navigate the platform through natural language commands from any page.

| Task ID | Task Name                                                           | Dependencies     |
| ------- | ------------------------------------------------------------------- | ---------------- |
| T109    | Shadow agent design tokens and CSS extensions                       | —                |
| T110    | Shadow Widget component (replaces AdvisoryFAB)                      | T109             |
| T111    | Command Surface overlay component                                   | T109, T110       |
| T112    | ShadowAgentContext provider (replaces AdvisoryPanelContext)         | T110, T111       |
| T113    | Platform action registry — intent classification and routing        | T111             |
| T114    | Advisory endpoint — command mode (short structured responses)       | T113             |
| T115    | Action execution — calculator dispatch from command surface         | T113, T114       |
| T116    | Action execution — navigation dispatch from command surface         | T113             |
| T117    | AppShell integration — remove old panel, wire new shadow components | T110, T111, T112 |
| T118    | Advisory deep workspace — preserve full chat page as research mode  | T117             |

---

## Milestone 14: Contextual Intelligence (Sprint 2)

**Goal**: AI-generated annotations appear on existing pages. A persistent margin strip shows compliance awareness and regulatory updates. The platform feels like it has ambient intelligence.

| Task ID | Task Name                                                                | Dependencies           |
| ------- | ------------------------------------------------------------------------ | ---------------------- |
| T119    | Shadow Margin component — collapsed strip (48px)                         | T109, T112             |
| T120    | Shadow Margin component — expanded card stack (320px)                    | T119                   |
| T121    | Shadow context API endpoint — compliance status, regulatory updates      | T119                   |
| T122    | Inline annotations — compliance page risk labels with fine amounts       | T121                   |
| T123    | Inline annotations — calculator result contextual notes                  | T121                   |
| T124    | Inline annotations — dashboard living briefing card                      | T121                   |
| T125    | Inline annotations — emergency page sector-specific notes                | T121                   |
| T126    | Annotation overlay system — context provider and rendering               | T122, T123, T124, T125 |
| T127    | Shadow Margin data sources — wire to compliance checker and admin alerts | T119, T121             |
| T128    | Mobile adaptation — bottom sheet for margin, full-screen for command     | T111, T119             |

---

## Milestone 15: Enterprise Model and Employee Interface (Sprint 3)

**Goal**: Multi-tenant platform with admin and employee roles. Admins invite employees. Employees see their own terms, leave balance, and company policies. Shadow agent adapts to each role. Observation layer begins learning user patterns.

| Task ID | Task Name                                                                   | Dependencies |
| ------- | --------------------------------------------------------------------------- | ------------ |
| T129    | Employee data model — Employee, LeaveBalance, CompanyPolicy entities        | T008         |
| T130    | Employee role — add EMPLOYEE to UserRole, extend tenant isolation           | T129         |
| T131    | Invitation system — create, send, accept invitation flow                    | T130         |
| T132    | Employee registration — invitation-based signup with role assignment        | T131         |
| T133    | Employee dashboard — My Terms, My Leave, employment summary                 | T132         |
| T134    | Employee leave view — balance display, entitlement breakdown                | T129, T133   |
| T135    | Company policies page — admin uploads, employees view                       | T129, T133   |
| T136    | Employee navigation — role-conditional sidebar (admin vs employee views)    | T130, T133   |
| T137    | Shadow agent employee scope — context injection scoped to own data only     | T130, T136   |
| T138    | Observation layer (Substrate) — session pattern extraction                  | T112, T137   |
| T139    | AI Memory settings page — view, edit, delete learned preferences            | T138         |
| T140    | Proactive insight surfacing — compliance gap age alerts, deadline reminders | T119, T138   |

---

## Summary

### Completed (T001-T108)

- **108/108 tasks complete** across 12 milestones
- Full advisory platform with 14-step safety chain
- Production deployed at aite.kailash.ai
- 7 red team rounds passed

### Active (T109-T140) — Shadow Agent Evolution

- **32 tasks active** across 3 milestones (M13-M15)
- M13 (10 tasks): Command surface, shadow widget, action registry
- M14 (10 tasks): Margin presence, inline annotations, contextual intelligence
- M15 (12 tasks): Enterprise multi-tenant, employee interface, observation layer
- Recommended order: M13 → M14 → M15 (sequential, each builds on the previous)
