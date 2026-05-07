# X — Cross-cutting

Concerns that span every milestone. Track here so they don't fall
through the gaps between M0-M10.

## X1 — Security review checklist (every ship, round-3 revised)

Run `security-reviewer` against the diff before each of M7, M8, M9 ships. Specific items always to check:

- [ ] Token kind isolation preserved (exit-only at v1; engagement-kind reserved for alumni-cycle v2+).
- [ ] Pseudonym secret never exposed in any API response or log.
- [ ] All admin endpoints have `require_role` enforced.
- [ ] **Manager-view endpoint enforces n≥5 + self-exclusion** (Z26).
- [ ] **In-app submit has CSRF guard + Idempotency-Key** (Z11, Z08).
- [ ] **Action endpoints whitelist mutable fields** (P39).
- [ ] Rate limits on every write endpoint.
- [ ] No PII (employee_id, name, email) in pseudonymous response payloads after submit.
- [ ] PDPA `consent_notice_version` recorded on every response.
- [ ] **PDPA admin-access log wired into every endpoint exposing employee_id** (Z16).
- [ ] CSV exports use `sanitizeCsvCell()` (rules/security.md).
- [ ] **`response_cohort_attributes` populated before identity stripping** (Z03).
- [ ] No secrets committed (`grep -E '(token|secret|password)' --include='*.py' --include='*.ts'` clean of literals).
- [ ] DataFlow updates use whitelists (P39).

## X2 — Anonymity invariants (continuous)

Six invariants that MUST hold from M3 onwards. If any of these breaks
between M3 and M10, that's an H-tier finding.

1. `anonymity_tier == "anonymous"` → `employee_id == 0` AND
   `employee_pseudonym == ""` after submit.
2. `anonymity_tier == "pseudonymous"` → `employee_id == 0` AND
   `employee_pseudonym != ""` after submit.
3. `anonymity_tier == "identified"` → `employee_id != 0` after submit.
4. Aggregator never returns a per-question OR per-cohort cell with
   `n < 5` AND `is_anonymity_safe == true`.
5. Manager view enforces `n ≥ 5` for the manager's direct + indirect
   reports.
6. Pseudonym is deterministic per (company, employee, survey) — same
   tuple always produces the same pseudonym; different tuple
   produces different pseudonym.

Pinned by `tests/regression/test_engagement_anonymity.py` (M6 T61).

## X3 — Performance budgets (round-3 revised)

Track these as smoke checks per ship:

| Operation                                      | Budget         | Source                                        |
| ---------------------------------------------- | -------------- | --------------------------------------------- |
| Cohort preview (28-employee company)           | <500ms p95     | M2 T23 — interactive                          |
| Launch endpoint (28-employee fan-out)          | <2s p95        | M3 T30 — synchronous                          |
| In-app render (`/my-responses/{id}/render`)    | <300ms p95     | M3 T31 — mounts on form open                  |
| In-app submit                                  | <1s p95        | M3 T31 — single insert + theme                |
| Aggregate endpoint (500 responses)             | <1s p95        | M3 T33 — HR view                              |
| **Trend endpoint (6 pulses, 28-employee co.)** | **<800ms p95** | **M3 T34 — hero chart on overview**           |
| **Manager view (n=20 direct + indirect)**      | **<1s p95**    | **M3 T35 (was P3, now P1)**                   |
| **Suggested actions (LLM call)**               | **<2s p95**    | **M3 T36 — cached 24h after first call**      |
| **Loop-closing endpoint**                      | **<500ms p95** | **M3 T38 — mounts on /my-engagement-surveys** |
| Cross-stage correlation (90-day window)        | <2s p95        | M8 T87 (was P3, now P2)                       |

## X4 — Observability

- **Logs:** every launch + submit logs at INFO with survey_id +
  tier (no PII for pseudonymous/anonymous).
- **Metrics (defer to v2 unless someone wires them):**
  `engagement.surveys.launched.total`,
  `engagement.responses.submitted.total{tier}`,
  `engagement.aggregate.duration_ms`.
- **Audit trail:** PDPA-relevant access (admin reading non-anonymous
  responses) flows through the existing `_log_pdpa_access()` helper
  per `auth-security.md`.

## X5 — Backwards-compatibility (round-3 revised)

**Engagement is in-app only at v1, so no engagement tokens are minted.** The token-kind isolation work in T01 still ships because exit-interview tokens need it: existing exit-interview tokens in the wild have no `kind` claim, and during the 30-day grace window they must keep working.

- T01 lands: 2026-MM-DD (P1 ship).
- Grace ends: T01 + 30 days. Treat missing `kind` as `"exit"` until then; reject afterwards.
- Cleanup: remove the legacy fallback in code (Z01 has the failing-test mechanism).
- Engagement-kind tokens reserved for future alumni-cycle feature; not minted at v1.

## X6 — Demo data hygiene (round-3 revised)

The seeded data MUST line up across exit-interviews + engagement + employment events + Goals to make the killer flow tell a complete story:

- **6 prior closed pulses** — Engineering trends 3.8 → 3.2 (drives the trend hero).
- 3 employees with `EmploymentEvent` `RESIGNED` in the last 90 days.
- All 3 have `ExitInterview` rows with themes; 2 cite "growth".
- All 3 have engagement responses in the recent pulses with low Likert on growth (P2 cross-stage demo).
- Pseudonyms link engagement → employment events for non-anonymous cases.
- **One accepted `EngagementAction`** with `linked_goal_id` pointing at a real seeded Goal — drives the loop-closing card AND the action panel "Already accepted" section.

If demo data drifts (e.g. someone resets the DB without re-running the seed), every demo surface loses its punch:

- Trend hero shows empty state.
- Action panel has nothing to say.
- Loop-closing card on Lily's view shows "no pulses closed yet".
- Cross-stage panel returns "Not enough data".

Document the seed-script run order in `scripts/README.md`.

## X7 — Open questions to resolve before /implement (round-3 revised)

- Q1. Lifecycle dashboard hero band — eNPS tile slots in at P2 (M8 T90), trend hero ships at P1. Confirm with uiux-designer that lifecycle hero still fits within 1280px viewport with engagement score added.
- Q2. Email service today — is it SendGrid, SES, or SMTP? T06 worker's transport client depends on this. (Note: round-3 dropped engagement-survey email fan-out; in-app notifications via existing Notification model. Email queue still relevant for exit-interviews and for P2 reminder send.)
- Q3. Does the existing `Notification` model cover the engagement-pending fanout (Z10)? Read first; extend if too narrow.
- Q4. When a manager has 4 reports + their own pseudonymous response, does THEIR response count toward n≥5? (**Decision: NO.** Z26 enforces self-exclusion.)
- Q5. Schedule cadence "monthly" — anchored to launch date or calendar month? (**Decision: anchored to launch date.** Z22 month-end clamp handles Jan 31 → Feb 28.)
- **Q6 (NEW round-3).** Goals module integration shape — how does the action panel's "create linked goal" call the existing Goals create endpoint? Read `goals.py` router to confirm the contract before M3 T37.
- **Q7 (NEW round-3).** AI-suggested actions deterministic fallback — confirm the 6-theme template list in M3 T36 covers the most common pulse outcomes. Likely safe; verify with `sg-employment-law-expert` for TAFEP / FWA neutrality of the suggestions ("audit promo cycle clarity" should not imply discrimination).
- **Q8 (NEW round-3).** Action visibility to managers — should the manager-view page show actions linked to their team's findings, or are actions HR-only at v1? (**Default: actions visible to assigned-manager if linked goal has them as owner.** Confirm.)

## X8 — Follow-ups from obayashi rounds 3-7

The work just closed left a few follow-ups (see
`workspaces/obayashi/.session-notes`). One specifically intersects
with engagement:

- "open issue: `/appraisals` AdminGuard blocks employees from their
  own My Appraisals tab — split route or loosen guard." Engagement
  has the same shape — make sure `/engagement` AdminGuard does NOT
  prevent the employee `/my-engagement-surveys` flow. They live in
  different routes, so this is structural; verify.
