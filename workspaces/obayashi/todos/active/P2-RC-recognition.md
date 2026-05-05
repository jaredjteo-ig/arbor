# Phase 2 — Recognition module

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 3 — Recognition.
**Estimate:** 4–5 dev-days.
**Why next:** smaller LOC than L&D; closes the Reward/Recognition/Benefits
half-implementation visible on the lifecycle dashboard's S6 panel.

## Goal

S6 reads as "Reward + Recognition + Benefits" — not just payroll + leave.
Employees can give kudos, managers can see a recognition feed, the
dashboard surfaces a recent-recognition tile.

## Critical path

```
P2-RC-1 (models) → P2-RC-2 (endpoints) → P2-RC-3 (page)
P2-RC-4 (dashboard widget) → after page lands
P2-RC-5 (seed) → after endpoints
P2-RC-6 (lifecycle hook) → last
P2-RC-7 (tests) → continuous
```

---

## P2-RC-1 — Recognition + PeerNomination models

- **Recognition fields:** `id`, `company_id`, `from_user_id`,
  `to_employee_id`, `category` (above_and_beyond / teamwork / customer
  / innovation / values), `message`, `is_public`, `created_at`.
- **PeerNomination fields:** `id`, `company_id`, `nominator_user_id`,
  `nominee_employee_id`, `period_id` (monthly award cycle),
  `category`, `rationale`, `created_at`.

## P2-RC-2 — POST/GET /recognition endpoints

- **Endpoints:**
  - `POST /recognition` — give kudos (any authenticated user).
  - `GET /recognition` — paginated; default scope = company-public; with
    `?to=me` returns kudos received by the current user.
  - `POST /recognition/nominate` — peer nomination (rate-limited to 5/day).
  - `GET /recognition/nominations?period=YYYY-MM` — admin tally.
- **Constraints:** rate-limited per `rules/security.md`; each write
  validated for `company_id` from the current user's session, never
  request body.

## P2-RC-3 — `/recognition` page (give kudos, see history)

- **Tabs:** Give Kudos | Public Feed | My Kudos (received).
- **Form:** Recipient picker (typeahead over active employees),
  Category dropdown, Message textarea (1000 char cap), Public toggle.
- **Feed:** card list with sender → recipient → message + timestamp.

## P2-RC-4 — Dashboard widget: this-month recognition feed

- **What:** New tile on `/dashboard` showing the 5 most recent public
  kudos. Click → `/recognition?tab=feed`.

## P2-RC-5 — Demo seed: 6 kudos across 4 employees

- **What:** Add a `seed_recognition` section to seed_demo_data.py.
  Idempotent; uses `lookup-company` + employee IDs from the directory.
- **Mix:** 4 categories represented; one private kudos for testing.

## P2-RC-6 — Lifecycle-dashboard hook (S6 sub-stage)

- **What:** Update the Gate 2 aggregator so S6's panel shows three
  sub-counters: Reward (last paid run), Recognition (kudos this month),
  Benefits (claims this month).
- **Health-pill:** S6 stays green if all three sub-counters are
  > 0 in the last 30 days; otherwise amber.

## P2-RC-7 — Regression + E2E tests

- **Regression:** category enum guard, public/private filter, rate
  limit pinned at 5/day for `nominate`.
- **E2E:** give a kudos, walk to `/recognition?to=me`, verify it
  appears.

---

## Done when

- S6 lifecycle panel shows three sub-counters lit up.
- Owner can demo "give a kudos → see it on the dashboard" in <30s.
- This file moves to `todos/completed/P2-RC-recognition.md`.
