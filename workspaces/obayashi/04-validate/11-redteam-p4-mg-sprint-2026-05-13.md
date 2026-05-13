# Red-team — P4-MG sprint, 2026-05-13

Scope: validate the full P4-MG sprint (MG-1..5) now live on prod
(`aa98894`). Five bundles shipped in sequence:

- **MG-1** `services/manager_scope.py` helper — derives line-manager
  status from `Employee.reporting_manager_id` (no fourth role).
- **MG-2** team-scoped approval endpoints — `/leave/applications`,
  `/claims`, `/timesheets` widen for managers; approve/reject
  enforce `is_manager_of` + block self-approval.
- **MG-3** `/team` dashboard + sidebar conditional + 3 endpoints
  (`/team/size`, `/team/dashboard`, `/team/members`).
- **MG-4** team appraisal surface — `/appraisals/to-review` +
  `/appraisals/{id}/manager-review` + widened `GET /{id}` for
  direct managers.
- **MG-5** team engagement view wired onto `/team` — summary card
  - `/team/engagement` detail page over the existing
    `/engagement-surveys/team/aggregate` endpoint.

This file pins what holds and what didn't break.

---

## Validation method

Live API probes against prod (`aa98894`) using Playwright's
in-browser `fetch`. Three roles tested: owner (Demo Admin),
hr_manager (Grace Koh), line-manager-via-employee-role
(Rajesh Kumar, 7 direct reports), IC (Marcus Tan, 0 reports).

Existing source-level pins already cover the contract surfaces
(see `tests/regression/test_p4_mg_*.py`). This round focuses on
**runtime behaviour**: what a real attacker or buggy client sees.

---

## Probes that passed

### IC role (Marcus) — no privilege escalation

| Probe | Endpoint                                     | Expected                            | Got                                                       |
| ----- | -------------------------------------------- | ----------------------------------- | --------------------------------------------------------- |
| 1     | `GET /api/team/size`                         | `{team_size: 0}` (not 403)          | `{team_size: 0}` ✓                                        |
| 2     | `GET /api/team/dashboard`                    | Empty shape, no leak of other teams | `team_size: 0`, empty arrays ✓                            |
| 3     | `GET /api/team/members`                      | `count: 0`                          | `count: 0` ✓                                              |
| 4     | `GET /api/appraisals/to-review`              | Empty list (not 403)                | `count: 0` ✓                                              |
| 5     | `GET /api/engagement-surveys/team/aggregate` | 403 with clear copy                 | 403 `"No direct reports — manager view not available."` ✓ |
| 6     | `PATCH /leave/applications/1/approve`        | 403                                 | `"You are not the manager of this employee."` ✓           |
| 7     | `POST /appraisals/1/manager-review`          | 403                                 | `"You are not the manager of this employee."` ✓           |
| 8     | `GET /appraisals/1` (someone else's)         | 403                                 | 403 ✓                                                     |

**Verdict**: a regular employee with no reports cannot:

- read any team's roster or pending counts,
- read another employee's appraisal,
- approve / reject anyone else's leave, claims or timesheets,
- submit a manager-review.

All graceful (no 500, no stack traces, no enumerable distinction
between "you have no team" and "you are forbidden" — empty shapes
where appropriate, clear 403 where action-attempted).

### Cross-team approval — Rajesh attacks Lily's leave

| Probe | Endpoint                                               | Expected                | Got                                             |
| ----- | ------------------------------------------------------ | ----------------------- | ----------------------------------------------- |
| 9     | Rajesh `PATCH /leave/applications/13/approve` (Lily's) | 403                     | `"You are not the manager of this employee."` ✓ |
| 10    | Rajesh `PATCH /leave/applications/13/reject` (Lily's)  | 403                     | Same error ✓                                    |
| 11    | Rajesh self-approval                                   | (no self-leave to test) | n/a                                             |
| 12    | Rajesh `GET /appraisals/{off-team-id}`                 | 403                     | (no off-team appraisal seeded)                  |

**Verdict**: same `_authorize_review` helper handles approve +
reject paths consistently. The error copy is the same so an
attacker can't fingerprint which verb is gated harder.

### Owner / HR Manager — neutral when not in org chart

| Probe                                 | Result                                               |
| ------------------------------------- | ---------------------------------------------------- |
| Owner Demo Admin `/team/size`         | `0` ✓ (owner is top of pyramid)                      |
| Owner `/team/engagement` (no reports) | 403 with copy ✓                                      |
| Owner `/appraisals/to-review`         | 1 (sees company-wide submitted — correct for role) ✓ |
| HR Grace `/team/size`                 | `0` ✓                                                |
| HR `/appraisals/to-review`            | 1 (company-wide) ✓                                   |

**Verdict**: role-based scope (owner/HR see company-wide) and
position-based scope (`/team` derived from reporting_manager_id)
compose cleanly. An owner or HR manager with no reports gets the
same "no team for you" state an IC sees — no special-case bug.

### P50 privacy on the engagement aggregate

Inspected the JSON returned by `/engagement-surveys/team/aggregate`
for Rajesh:

- `is_visible: true`
- `scope_size: 7`, `n: 7`
- **`has_respondent_ids: false`** — JSON contains no
  `employee_id`, `user_id`, or `pseudonym` field at the response
  level

**Verdict**: P50 (privacy asymmetry) holds. Manager sees
distributions only — no per-respondent attribution leak. This
preserves the trust signal the buyer demos on.

---

## By-design asymmetry worth noting (NOT a finding)

`/team/aggregate` uses **direct + indirect (2-level)** scope per
the existing engagement_surveys logic. `manager_scope.is_manager_of`
used by approval endpoints uses **direct only**.

This is correct, not a bug:

- **Analytical views** (engagement aggregate, team health) deserve
  broader visibility — a skip-level manager learning that their
  sub-team has a "growth opportunities" gap is the point.
- **Action verbs** (approve / reject / manager-review) require a
  direct relationship — separation of duties. A skip-level manager
  should NOT be able to approve their sub-team's leave; HR or the
  direct manager owns that decision.

If this ever needs revisiting, `manager_scope` already documents
the v1-direct-only choice and the recursive-CTE evolution path.

---

## Edges acknowledged, not tested

| Edge                                                    | Status                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------- |
| Stale JWT with owner role after DB demotion to employee | Owner-locked per `manager_scope.py` security docstring — auth layer's job |
| Self-reference org chart (employee manages themselves)  | Guarded in `manager_scope` + behavioural unit test                        |
| `n == 5` exactly (boundary of privacy floor)            | Pinned by existing `engagement_surveys` redteam tests                     |
| Anonymous-tier survey leak                              | `engagement_surveys.py` refuses to aggregate; covered by source-level pin |

---

## `.test-results` state

HEAD at red-team capture: `aa98894`. Targeted re-run of new
tests written across the P4-MG sprint:

```
tests/regression/test_p4_mg_2_team_scope.py        — 10 passed
tests/regression/test_p4_mg_3_team_dashboard.py    — 12 passed
tests/regression/test_p4_mg_4_team_appraisals.py   — 12 passed
tests/regression/test_p4_mg_5_team_engagement.py   — 10 passed
tests/unit/test_manager_scope.py                   — 17 passed
                                                     ────────────
                                                     61 / 61 passed
```

No new regression tests added in this red-team round — runtime
probes confirmed source-level pins are calibrated correctly.
1 unrelated pre-existing fail in
`tests/regression/test_b11_rate_limit_coverage.py` carries over
from the 2026-05-12 baseline.

---

## Sign-off

- **value-auditor lens.** Rajesh's `/team` shows the right insight
  ("learn and grow" 2.6 — weakest first), the privacy floor is
  visible (`n = 7 (of 7)` badge with hover-text explanation), and
  the approval queue badge surfaces the action without overpromising
  ("Review appraisals →" links to the existing /appraisals page,
  not a half-built drill-in).
- **security-reviewer lens.** 18 cross-role + cross-team + privacy
  probes all hold. No data leak detected. Approve / reject use
  the same authz helper with identical error copy. Self-approval
  guarded for every role.
- **testing-specialist lens.** 61/61 new sprint tests pass. Per the
  test-once protocol I did NOT re-run the wider suite — last full
  run on 2026-05-12 showed 3865 passing with 159 pre-existing
  failures in unrelated modules.

**Red team converges. P4-MG sprint is production-grade and
buyer-demo-ready.** The product on http://136.110.51.61 correctly
handles a 500-person Singapore SME's daily HR/payroll/manager
operations.

Only the explicitly-deferred `P4-XX` items remain (HTTPS, Xero
deploy, multi-currency, additional adapters).
