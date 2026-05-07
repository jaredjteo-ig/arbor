# Z — Red-team amendments (round 2)

Source: `04-validate/02-todo-redteam-findings.md`. Round-2 deep-analyst
review surfaced 14 H + 23 M + 11 L gaps the milestone files miss.

This file is the patch set: every new task or acceptance-criterion
amendment needed before `/implement` starts. The implementor folds
each amendment into the milestone it belongs to.

Tasks here are numbered Z01..Zxx (kept distinct from T## to make the
amendments easy to track). Each Z-task names the host milestone.

## Amendments to M0 — Foundations

### Z01 — Token grace expiry test (covers H8, L1)

- **Where:** Add to M0 alongside T01.
- **What:** Write a `tests/regression/test_token_kind_grace.py` that
  passes today but FAILS 30 days after T01 lands. Mechanism: pin
  `T01_LANDED_AT` constant; assert `if datetime.utcnow() > T01_LANDED_AT

* timedelta(days=30): assert "kind" in decoded_legacy_token`.

- **Plus:** counter `legacy_token_kind_assumed_total` incremented
  every time the legacy fallback fires; surfaces in logs.
- **Acceptance:** test green today; log emits counter when an
  unkinded token is verified.

### Z02 — Pseudonym secret versioning (covers H11)

- **Where:** Replace T03's single-field design.
- **What:** `Company.engagement_secret_active_version: int` plus
  versioned secret storage (`engagement_secret_v1`, `..._v2`, …).
  Responses store `pseudonym_version: int`. Verification routes by
  version.
- **Rotation runbook:** documented as part of T03 acceptance — what
  triggers rotation (annual default, or on incident); what stays
  valid post-rotation.
- **Acceptance:** rotation test produces NEW pseudonyms post-rotation
  for the same (employee, survey) tuple; pre-rotation pseudonyms
  remain valid for trend reads up to the rotation point.

## Amendments to M1 — Data model

### Z03 — Frozen cohort attributes on response (covers H2)

- **Where:** Add field to `EngagementSurveyResponse`.
- **What:** New `response_cohort_attributes: str` (JSON) populated
  on submit BEFORE identity stripping. Snapshots:
  `{department, pass_type, tenure_band, manager_id_hashed}`.
- **Why:** the aggregator must compute by-cohort stats without
  joining `Employee` (since pseudonymous/anonymous rows have no
  employee_id). Single-employee cohorts (e.g. one Eng + free text)
  still leak; aggregator's `n>=5` gate handles that downstream.
- **Acceptance:** every submitted response has the field populated;
  the aggregator's `by_cohort` tab uses ONLY this field, never a
  live `Employee` join. Pinned by test.

### Z04 — Termination semantics for already-submitted (covers M11)

- **Where:** T17 acceptance.
- **What:** Explicit rule: termination void only affects rows with
  `submitted_at IS NULL`. Submitted responses are NOT voided —
  they were given while the employee was active and stay in the
  aggregate.
- **Acceptance:** test pinning the boundary: terminate an employee
  who has both a submitted and a pending response → submitted stays,
  pending → `is_void=True`.

### Z05 — Migration rollback test (covers M20)

- **Where:** T15 acceptance.
- **What:** "Apply migration → seed 5 rows across all 5 tables →
  `alembic downgrade -1` → assert clean uninstall (no orphan indexes,
  no orphan FK constraints)."
- **Why:** asserting reversibility without testing it has bitten the
  team in past. Pin the boundary.

## Amendments to M3 — Launch + responses API

### Z06 — Per-tenant launch lock (covers H3)

- **Where:** Add to T30.
- **What:** Acquire per-`company_id` lock for the launch transaction
  (Postgres advisory lock OR `threading.Lock`). Inside the lock,
  re-run overlap check against freshly-read open surveys. Pattern
  P-per-tenant-locks.
- **Acceptance:** parallel-launch test (`pytest -n 2`) — two threads
  hitting the same cohort produce one survey, not two.

### Z07 — Atomic response_count (covers H4)

- **Where:** Add to T31 + T32 submit handlers.
- **Decision:** denormalised counter with atomic SQL increment OR
  derive on read. Pick: **derive on read** (simpler, no integrity
  burden, P95 still under 1s for 500 responses per the X3 budget).
- **What:** Drop `response_count` denormalised column from
  `EngagementSurvey`. Replace every read with
  `SELECT count(*) FROM engagement_survey_responses WHERE survey_id=?
AND submitted_at IS NOT NULL AND is_void=False`.
- **Acceptance:** parallel-submit test with 10 threads → exactly 10
  reflected in detail page, never 9 or 11.

### Z08 — Idempotency on public submit (covers H5)

- **Where:** T31 public submit.
- **What:** Accept `Idempotency-Key` header. Derive default key from
  `sha256(token + canonical_payload)` if not supplied. Store keyed
  hash on the response row. Replay with same key returns prior
  response unchanged (200, body `{ok: true, idempotent_replay: true}`).
- **Acceptance:** identical submit twice → one row; same token,
  different payload → 409 already_submitted.

### Z09 — Launch saga rollback (covers H6)

- **Where:** T30.
- **What:** Structure launch as three stages with reverse-order
  compensation:
  1. Create `EngagementSurvey` row (transactional).
  2. Bulk-create response rows (transactional).
  3. Bulk-enqueue emails (post-commit, at-least-once delivery).
- **On failure of stage 3:** survey gets
  `email_delivery_status: "partial"`. Detail page surfaces banner
  "14/28 emails delivered, 14 retrying — Retry queue". Admin can
  click to retry.
- **On failure of stage 1 or 2:** rollback the transaction; nothing
  half-created.
- **Acceptance:** kill the email queue mid-launch → survey detail
  shows partial banner; backend `email_delivery_status="partial"`;
  retry button rebuilds the queue.

### Z10 — In-app notification fanout (covers H7)

- **Where:** T30 launch (post-commit hook).
- **What:** For each response row, create a `Notification` row
  (`kind="engagement_pending"`, `link="/my-engagement-surveys/{response_id}"`,
  `actor_id=launching_admin_id`).
- **Frontend:** `/my-dashboard` reads existing notification feed;
  pending card derived from there (already render path; just data).
- **Investigation cue:** confirm the existing `Notification` model
  covers the required fields; if not, extend it (don't fork a new
  model).
- **Acceptance:** post-launch, `GET /notifications/me` includes one
  row per recipient; Lily's dashboard pending card visible immediately.

### Z11 — CSRF on in-app submit (covers H9)

- **Where:** Add to T32.
- **What:** `POST /engagement-surveys/my-responses/{id}/submit`
  enforces `Origin`/`Referer` matches configured app origin OR
  requires CSRF token header (pick whichever the rest of the platform
  already does — read `auth-security.md` to confirm).
- **Acceptance:** cross-origin POST with valid bearer is rejected
  403; same-origin proceeds normally.

### Z12 — closes_at validation (covers M7, M8)

- **Where:** Add to T30.
- **What:** Reject launches where `closes_at <= launched_at + 1h`
  (1h floor prevents fat-finger). Reject `closes_at` more than 90
  days out (sanity bound).
- **Plus timezone:** wizard sends ISO-8601 with explicit `+08:00`
  offset; backend stores UTC; aggregations and display convert back
  to SGT.
- **Acceptance:** launch with past `closes_at` → 400. Display "21
  May 23:59 SGT" matches DB `2026-05-21T15:59:59Z`.

### Z13 — PII-clean error envelopes (covers M15)

- **Where:** Add to T31 + T32.
- **What:** FastAPI validation errors on public + employee submit
  endpoints return generic `{detail: "Invalid request",
correlation_id: "<uuid>"}` without echoing input fields. Log the
  full validation error server-side keyed by correlation_id for
  debugging.
- **Acceptance:** malformed payload with email in `employee_id`
  field → response body excludes the email; server log includes it.

### Z14 — Rate limits on `/render` and `/validate` (covers M17)

- **Where:** Add to T31.
- **What:** `/render` 30 req/min/token; `/validate` 60 req/min/IP.
  Returns 429 with `Retry-After` header.
- **Acceptance:** flooding either endpoint at 100 req/min → 429
  after the threshold.

### Z15 — CORS for public route (covers M16)

- **Where:** Add to X1 checklist + T31.
- **What:** Public `/engagement-surveys/public/**` endpoints document
  allowed origins explicitly. `Credentials: omit` (tokens are
  url-bound, no cookie). Preflight returns 204 with explicit
  allow-origin / allow-headers / allow-methods.
- **Acceptance:** Playwright smoke from a localhost origin returns
  204 on OPTIONS for the configured prod origin; rejects others.

### Z16 — PDPA admin-access audit log (covers H12)

- **Where:** Add to T33 (admin response list) + every endpoint
  returning non-zero `employee_id`.
- **What:** Wire `_log_pdpa_access(actor_id=current_user.id,
subject_employee_id=row.employee_id, purpose="engagement_admin_read",
resource=f"survey/{survey_id}/response/{response_id}")` on:
  - `GET /surveys/{id}/responses`
  - `GET /surveys/{id}/export` (when M9 P2 ships)
  - The expand-detail endpoint
- **Acceptance:** regression test asserts a `PdpaAccessLog` row
  after every admin read of an identified response.

## Amendments to M5 — Frontend: employee

### Z17 — Mobile-responsive public form (covers M12)

- **Where:** Add to T54 (public page).
- **What:** Tested at 375x667 (iPhone SE) viewport in Playwright.
  Tap targets >=44pt. ChipMultiSelect wraps. Long-text auto-grows
  on mobile keyboard. Submit button reachable above keyboard.
- **Acceptance:** Playwright test pinned at 375x667 viewport.

### Z18 — Accessibility: axe-core scan (covers M13)

- **Where:** Add to T54 (public) + T52 (in-app form).
- **What:** axe-core scan returns zero serious violations on
  `/engagement-survey/[token]` and `/my-engagement-surveys/[id]/respond`.
  ARIA: Likert5 = `role="radiogroup"`, EnpsScale =
  `role="radiogroup" aria-label="Net promoter score 0 to 10"`.
- **Acceptance:** axe-core in Playwright suite returns 0 serious.

### Z19 — Engagement empty-state copy authored (covers M23)

- **Where:** Add to T54.
- **What:** Five empty states with copy + screenshot test:
  invalid_or_expired, not_found, already_submitted, closed, voided
  (the new state from C1).
- **Acceptance:** five Playwright snapshots stable across runs.

### Z20 — Lily route boundary smoke (covers L11)

- **Where:** Add to T55.
- **What:** Playwright smoke as Lily — confirm `/engagement` returns
  403 (or sidebar hidden) AND `/my-engagement-surveys` returns 200.
- **Acceptance:** test pinned; engagement leakage to employees
  caught in CI.

## Amendments to M6 — Demo seed + tests

### Z21 — Voided submit test matrix (covers H10)

- **Where:** Expand T61 anonymity-invariants suite.
- **What:** 12-cell test matrix:
  `(public-submit, in-app-submit) × (is_void=True, is_void=False) ×
(anonymity_tier ∈ {identified, pseudonymous, anonymous})`.
  Voided rows return 410 in every cell. `/my-pending` excludes
  voided. `/aggregate` excludes voided.
- **Acceptance:** all 12 cells pinned.

## Amendments to M8 — P2 schedules + exports

### Z22 — Schedule month-end clamp (covers M21)

- **Where:** Add to T80 cron tick.
- **What:** If `next_launch_at` target day > month length, clamp
  to last day of month. Schedule anchored Jan 31 → fires Feb 28
  (or Feb 29 leap), Mar 31, Apr 30.
- **Acceptance:** cron-tick test crossing month boundary correct.

### Z23 — Auto-close cron (covers M22)

- **Where:** Add to T80.
- **What:** Daily tick at 02:30 SGT scans surveys with `closes_at <
now AND closed_at IS NULL`, sets `closed_at = now`, fires close
  notification to HR. Idempotent.
- **Acceptance:** survey with past `closes_at` auto-closes on next
  tick; re-running tick is no-op.

### Z24 — CSV export sanitisation (covers M18)

- **Where:** Add to T85 export endpoint.
- **What:** Every cell passes through `sanitizeCsvCell()` (per
  rules/security.md). Specifically `=`, `+`, `-`, `@`, tab, CR
  prefixes are escaped with `'`.
- **Acceptance:** payload `=cmd|/c calc.exe` exports as
  `'=cmd|/c calc.exe`; `=HYPERLINK("evil")` neutralised.

## Amendments to M9 — P3 cross-stage + manager view

### Z25 — Cross-stage correlation endpoint contract (covers H1)

- **Where:** Replace T90's loose service spec with a concrete
  endpoint.
- **What:** `GET /strategy/lifecycle/engagement-resignation-correlation?window_days=90`
  returning:
  ```json
  {
    "window_days": 90,
    "resigned_count": 3,
    "low_engagement_resigned_count": 2,
    "pseudonym_join_strategy": "by_pseudonym|by_employee_id",
    "sample_employees": [
      {
        "display_label": "Rajesh Kumar | Anonymous Engineering, T-15d",
        "exit_themes": ["growth", "manager"],
        "last_engagement_likert_avg": 2.1,
        "days_between_pulse_and_resignation": 47,
        "anonymity_tier": "pseudonymous"
      }
    ]
  }
  ```
- **Join logic:** `EmploymentEvent` RESIGNED in window → join
  `EngagementSurveyResponse` by `employee_id` (identified) or
  `employee_pseudonym` (pseudonymous). Anonymous tier is excluded
  from the join (by design — no link possible).
- **Suppression:** if fewer than 2 correlated rows, return
  `{message: "Not enough data for cross-stage correlation"}`.
- **Acceptance:** against seeded data (Z27), returns >=2 correlated
  rows. Anonymous-only surveys produce empty join.

### Z26 — Manager-view self-exclusion (covers H13)

- **Where:** Add to T93.
- **What:** Manager-view aggregator filters out
  `employee_id == current_manager_employee_id` (and the equivalent
  pseudonym, derived from manager's own (company_id, employee_id,
  survey_id) HMAC) before computing `n`. Then re-evaluates `n >= 5`.
- **Acceptance:** three test rows:
  1. Manager + 4 reports → "Roll up to skip-level" banner.
  2. Manager + 5 reports + manager's own response → "n=5" view
     (manager's own excluded).
  3. Manager + 5 reports without manager's own response → "n=5"
     view.

### Z27 — Engagement seed entries (covers H14)

- **Where:** Add to T-seed (or extend the existing seed-script
  workspace milestone).
- **What:** Extend `scripts/seed_demo_data.py` with two new sections:
  - `engagement-templates` — seed Q12 + monthly_pulse if not present
    (idempotent).
  - `engagement-history` — create 2 closed pulses + responses
    linked by pseudonym to the 3 RESIGNED employees from the
    existing exit-interview backfill. The 2 employees who cited
    "growth" in exit get Likert 1-2 on the growth-related Q4. The
    third gets Likert 3.
- **Plus:** open pulse with 22/28 responses; Lily yet to respond.
- **Anchor:** uses fixed RNG seed for reproducibility.
- **Acceptance:** running on a fresh demo DB with `--section
demo-refresh` produces:
  - Engagement overview hero "3.6 / 5 · 22 of 28 · eNPS +18".
  - Cross-stage panel returns >=2 correlated rows.

## Amendments to M10 — Quality + docs

### Z28 — i18n schema reservation (covers M14)

- **Where:** Add to T103 codify list.
- **What:** Document explicitly: "v1 ships English-only; template
  `sections` JSON shape supports `text_translations: {en, zh, ms}`
  for v2." Reserve the schema field even if not implemented, so
  v2 doesn't migrate.

### Z29 — Cohort preview perf gate (covers L8)

- **Where:** Add to T100 audit.
- **What:** Smoke perf test asserting cohort preview returns in
  <500ms with seeded 100-employee company. Fails CI on regression.

## Amendments to X — Cross-cutting

### Z30 — Decision points to resolve before /implement

The red team surfaced 7 stakeholder decisions. Add to X7 (Open
questions) so they're visible to the human reviewer:

- **D1.** Confirm the cross-stage correlation endpoint path matches
  Z25's proposed contract.
- **D2.** Approve the cohort denormalisation approach (Z03 frozen
  attributes) vs alternatives (live join with anonymity-tier-aware
  routing, or by-cohort tab limited to identified surveys only).
  This is the highest-leverage architectural decision.
- **D3.** Confirm derive-on-read for `response_count` (Z07) vs
  atomic counter. Decision: derive-on-read for v1.
- **D4.** Confirm saga shape (Z09): partial-delivery surfaced to HR
  vs full rollback on email failure. Decision: partial-delivery,
  per Lily flow Step 4.
- **D5.** Pseudonym secret rotation cadence (Z02): annual? On
  staffing change? Incident only? Default: annual + on incident.
- **D6.** i18n scope for v1: English-only at v1, Z28 reserves the
  schema. Confirm.
- **D7.** PDF export: ship at v1 or defer to v2 (CSV-only v1)?
  Default: defer (Z24 covers CSV; PDF in v2).

### Z31 — Operational observability (covers L1, X4)

- **Where:** Update X4.
- **What:** Wire concrete metric names:
  - `engagement.surveys.launched.total{tenant}`
  - `engagement.responses.submitted.total{tier, tenant}`
  - `engagement.aggregate.duration_ms`
  - `engagement.legacy_token_kind_assumed_total` (Z01)
  - `engagement.email.delivery_partial_total` (Z09)
- **Acceptance:** P3 ship checklist confirms metrics emit; alerting
  hooks deferred to v2 unless explicit ask.

## Acceptance for Z

When `/implement` reads this file alongside the milestone files,
each Z-task has been folded in. The Z file is the authoritative
amendment surface; the original milestone files stay readable but
incomplete without Z.

After /implement closes M0-M10, this file moves to `todos/completed/`
intact (alongside its host milestones).

## Status

- 14 H findings → 14 Z-tasks (Z01-Z16, Z21, Z25-Z27).
- Critical M findings → 13 Z-tasks (Z04, Z05, Z12-Z15, Z17-Z19,
  Z22-Z24, Z28).
- L findings rolled in opportunistically (Z20, Z29, Z31).

Total Z-tasks: 31 amendments folded back into M0/M1/M3/M5/M6/M8/M9/M10/X.

## Round-3 product revision — invalidated / superseded amendments

After the round-3 product revision (`02-plans/04-product-revision-round3.md`), several Z amendments are no longer needed because the engagement-survey public route was dropped entirely. Engagement is in-app only.

### Invalidated by round-3 (no longer applicable)

- **Z08 (idempotency on PUBLIC submit) — REPLACED.** The shape now applies to in-app submit only. M3 T31 owns it.
- **Z14 (rate limits on `/render`/`/validate` PUBLIC endpoints) — DROPPED.** No public engagement endpoints to rate-limit. Token kind grace (Z01) still applies because exit-interview tokens still exist.
- **Z15 (CORS for PUBLIC route) — DROPPED.** No public engagement route. CORS for exit-interview public route is unchanged.
- **Z17 (mobile-responsive PUBLIC form) — DROPPED.** No public engagement route. The in-app form (T51) inherits the existing app shell's responsiveness.
- **Z19 (engagement empty-state copy on PUBLIC route) — DROPPED.** No public route. In-app form's empty state is the existing dashboard pattern.

### Still applicable (folded into round-3 milestones)

- Z01-Z07, Z09-Z13, Z16, Z18, Z20-Z24, Z26-Z29, Z31 all still apply as written.
- Z10 (in-app notification fanout) is now THE fanout mechanism (no email for engagement at P1).
- Z25 (cross-stage correlation endpoint) is now M8 T87, not M9.
- Z26 (manager-view self-exclusion) is now M3 T35 + M4 T44 (P1, not P3).

### New amendments from round-3

- **Z32. EngagementAction model** (M1 T17a) — captures the action loop. New table.
- **Z33. Trend endpoint + cohort param** (M3 T34) — backs the hero chart. Reads from `response_cohort_attributes` (Z03) for non-identified surveys.
- **Z34. Suggested-actions LLM call + deterministic fallback** (M3 T36) — light Kaizen with 6-theme deterministic fallback per D8.
- **Z35. Action endpoints (create / patch / list)** (M3 T37) — wires accept-and-create-goal flow. Auto-anchors next-pulse question.
- **Z36. Loop-closing card endpoint** (M3 T38) — drives the trust-builder card on `/my-engagement-surveys`. Reveals top theme + accepted action + linked goal label.
- **Z37. Manager-view tab** (M4 T44) — pulled from P3. Non-admin route gated by `has_direct_reports`. Self-exclusion (Z26) baked in.
- **Z38. Action panel on detail page** (M4 T46) — 3 suggestions + accept/edit/reject + create-linked-goal modal + already-accepted section.
- **Z39. Trend hero on overview** (M4 T41) — replaces single-pulse hero. Cohort dropdown reloads chart.
- **Z40. Loop-closing card on employee view** (M5 T50) — top of `/my-engagement-surveys`. Hidden when no closed pulses.
- **Z41. Anonymity-badge revised copy** (M5 T51) — three-tier explanation in human language with explicit "free-text comments may be readable to HR" warning on pseudonymous + anonymous.
- **Z42. Demo seed expansion** (M6 T60) — 6 prior pulses + 1 accepted action + linked goal + Engineering descending trend.
- **Z43. Action-loop regression tests** (M6 T66) — covers create-goal, auto-anchoring, manager self-exclusion 3-row matrix.

Total Z-tasks after round-3: 31 (round-2) − 5 invalidated + 12 new = **38 Z-tasks**.
