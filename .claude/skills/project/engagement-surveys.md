---
name: engagement-surveys
description: "Engagement survey product — pulse surveys, three-tier anonymity (identified / pseudonymous / anonymous), HMAC pseudonyms with versioned secrets, action loop closing back to employees, manager team aggregate with self-exclusion, 6-pulse trend, Q12 / monthly_pulse templates, cohort builder, saga launch with partial-delivery state, in-app respond form, loop-closing card narrative, and the 13 numbered Z-amendments + B/D/C phase fixes that hardened the pipeline. Use when working on apps/web/src/app/(dashboard)/engagement/, apps/web/src/app/(dashboard)/my-engagement-surveys/, src/hr_advisory/api/routers/engagement_surveys.py, scripts/backfill_demo_engagement_surveys.py, or any engagement-survey-adjacent code."
---

# Engagement Survey Patterns

Project-specific knowledge for the Arbor engagement-survey product:
how the three anonymity tiers actually work, where the killer-flow
narrative lives in code, what the Z01-Z44 numbered amendments mean,
and the gotchas you'll hit on day one.

If you're touching anything in `engagement_surveys.py` or the
`/engagement/*`, `/my-engagement-surveys/*`, or `/engagement/team`
frontend routes — read this first.

## Files of record

| File                                                                                                       | What it owns                                                                                               |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `src/hr_advisory/api/routers/engagement_surveys.py`                                                        | 28-endpoint router (~2200 lines): templates, cohorts, surveys, responses, team aggregate, actions, history |
| `src/hr_advisory/services/engagement_pseudonym.py`                                                         | HMAC-SHA256 pseudonym computation + versioned secret rotation (Z02)                                        |
| `src/hr_advisory/services/cohort_resolver.py`                                                              | `resolve_cohort()` + `validate_filter_spec()` (P1 single-dimension only)                                   |
| `src/hr_advisory/services/theme_tagger.py`                                                                 | Generalised theme keyword sweep (sanitises free-text via `sanitise_input` first)                           |
| `src/hr_advisory/services/engagement_actions.py`                                                           | Loop-closing payload + 18 deterministic fallback action templates (sg-employment-law-expert reviewed)      |
| `src/hr_advisory/services/engagement_termination.py`                                                       | Z04 — only voids `submitted_at IS NULL` rows on exit                                                       |
| `src/hr_advisory/services/engagement_library.py`                                                           | Q12 + monthly_pulse seed entries                                                                           |
| `src/hr_advisory/services/notifications.py`                                                                | `bulk_create_engagement_pending` (returns count for Z09 saga partial state)                                |
| `apps/web/src/services/api/engagement.ts`                                                                  | Typed API surface, `describeAnonymityTier(tier, hasFreeText)`, `templateHasFreeText`                       |
| `apps/web/src/app/(dashboard)/engagement/page.tsx`                                                         | HR overview: trend hero + 3 tabs (Surveys / Templates / Cohorts) + launch wizard                           |
| `apps/web/src/app/(dashboard)/engagement/surveys/[id]/page.tsx`                                            | Survey detail: aggregated / by-cohort / responses tabs + action panel                                      |
| `apps/web/src/app/(dashboard)/engagement/team/page.tsx`                                                    | Manager team aggregate: avg + per-question + 6-pulse trend (n>=5) / themes-only (n=3-4) / suppressed (n<3) |
| `apps/web/src/app/(dashboard)/my-engagement-surveys/page.tsx`                                              | Employee landing: loop-closing card + pending check-ins + history                                          |
| `apps/web/src/app/(dashboard)/my-engagement-surveys/[response_id]/respond/page.tsx`                        | In-app response form with progress counter + privacy banner                                                |
| `apps/web/src/components/engagement/{TrendChart,SurveysTab,TemplatesTab,CohortsTab,LaunchWizard,Stat}.tsx` | Engagement-specific UI primitives                                                                          |
| `apps/web/src/components/surveys/{Likert5,EnpsScale,ChipMultiSelect,ScoreBar}.tsx`                         | Reusable form primitives                                                                                   |
| `scripts/backfill_demo_engagement_surveys.py`                                                              | Demo seed: 6 prior closed pulses + 1 open + 1 accepted action + linked goal                                |
| `tests/integration/test_engagement_surveys_api.py`                                                         | 18 integration tests pinning M0-M2                                                                         |
| `tests/integration/test_engagement_surveys_m3.py`                                                          | 19 integration tests pinning M3 (launch + responses + aggregate)                                           |
| `tests/regression/test_redteam_phase{1,2}_fixes.py`                                                        | 19 regression tests pinning B1-B7 + D1-D4                                                                  |
| `tests/regression/test_engagement_pseudonym.py` + `test_cohort_resolver.py` + ...                          | Unit tests for the helper services                                                                         |

## Three-tier anonymity model

The product offers three tiers per survey, chosen at launch and
frozen on the survey row (`anonymity_tier` column). Tier determines
both storage and aggregation behaviour:

| Tier           | `employee_id` at submit | `employee_pseudonym` | History visible to employee?                                  | Manager aggregate?                                         |
| -------------- | ----------------------- | -------------------- | ------------------------------------------------------------- | ---------------------------------------------------------- |
| `identified`   | real employee id        | empty                | Full row                                                      | filter on employee_id                                      |
| `pseudonymous` | zeroed (0)              | HMAC-SHA256 digest   | survey_name + submitted_at + tier badge (no themes — see P50) | filter on pseudonym, exclude manager's own pseudonym (Z26) |
| `anonymous`    | zeroed (0)              | empty                | Hidden — no trail to recover                                  | rejected entirely (no per-team attribution)                |

The tier is enforced at three points:

1. **Submit (`submit_my_response`)** — branches to set
   `employee_id=0` and compute `employee_pseudonym` for pseudonymous,
   or zero both for anonymous.
2. **Aggregate (`get_team_aggregate`, `_build_aggregate`)** — uses
   the right scope predicate (employee_id vs pseudonym vs reject).
3. **History (`my_history`)** — recomputes the data subject's own
   pseudonym to surface her own pseudonymous submissions while
   keeping HR-side anonymity intact (see P50 in
   `security-patterns.md`).

**Z02 — Versioned secret rotation:** the `Company` row carries
`engagement_secret_v1`, `_v2`, and `engagement_secret_active_version`.
On rotation, set `_v2` and bump `_active_version`. The pseudonym
computation reads `_active_version` to pick the right secret, so
old responses keep their old pseudonyms (no retroactive
re-identification).

**MIN_COHORT_SIZE = 5 / THEMES_ONLY_THRESHOLD = 3:** the SG-SME
floor for showing aggregate data. n<3 suppress entirely; 3≤n<5
themes-only; n≥5 full aggregate. D1 in red-team Phase 2 introduced
the themes-only band because at 28-employee scale, line managers
with 4-7 reports almost never reach n≥5 — suppressing entirely
made the page useless.

## The killer flow narrative — where each piece lives

```
     ┌────────────────────────────────────┐
     │ Employee responds (pseudonymous)   │  /my-engagement-surveys/[id]/respond
     │ Theme tagger extracts "growth"     │  services/theme_tagger.py
     └─────────────────┬──────────────────┘
                       │
     ┌─────────────────▼──────────────────┐
     │ HR sees aggregate + suggested      │  /engagement/surveys/[id]
     │ actions for the lowest cohort      │  GET /surveys/{id}/suggested-actions
     └─────────────────┬──────────────────┘
                       │
     ┌─────────────────▼──────────────────┐
     │ HR accepts → linked Goal created   │  POST /surveys/{id}/actions
     │ EngagementAction stores theme (D4) │  services/engagement_actions.py
     └─────────────────┬──────────────────┘
                       │
     ┌─────────────────▼──────────────────┐
     │ Loop-closing card mirrors back     │  /my-engagement-surveys
     │ "Last pulse you raised growth.     │  GET /my-loop-closing
     │ HR did: <action>. Linked to:       │
     │ <goal>. Next pulse will ask: ..."  │
     └─────────────────┬──────────────────┘
                       │
     ┌─────────────────▼──────────────────┐
     │ Next pulse anchors a question on   │  scripts/backfill_demo_engagement_surveys.py
     │ the same theme. Trend measures the │  trend hero on /engagement
     │ effect over time.                  │
     └────────────────────────────────────┘
```

Each step has a specific file. If the narrative breaks for a buyer
during demo, walk this list — most failures are in one specific
step rather than systemic.

## Numbered amendments — Z01–Z44

The Z-numbered amendments came from three rounds of red-team review
that shipped before P1. They're enforced in the code with comments
referencing the number. When you see `# Z06` in the router, that's
this catalogue.

| #   | What                                                                                           |
| --- | ---------------------------------------------------------------------------------------------- |
| Z01 | Round 3 — drop public tokenised path; in-app only at v1                                        |
| Z02 | Versioned secret rotation (`engagement_secret_v1` / `_v2` / `_active_version`)                 |
| Z03 | Frozen cohort attributes on response — never live-join to current employee row                 |
| Z04 | Termination only voids `submitted_at IS NULL` (don't void already-submitted responses)         |
| Z06 | Per-company `_LAUNCH_LOCKS` `threading.Lock` to serialise concurrent launches                  |
| Z08 | Submit idempotency window (existing-row check before insert)                                   |
| Z09 | Saga delivery_status: launch returns `complete` / `partial` / `failed` based on notify success |
| Z11 | CSRF / Origin allowlist via `settings.cors_origins_list()` (post-C3)                           |
| Z12 | `closes_at` validation — must be ≤ 90 days out                                                 |
| Z21 | Voided check on submit — refuse to accept submission against voided response                   |
| Z26 | Manager self-exclusion in `/team/aggregate` (don't include manager's own response)             |
| Z41 | Revised anonymity-tier copy (post-walk #67 made the free-text caveat conditional)              |

The B (red-team Phase 1, ship-blocker) / D (Phase 2, demo readiness)
/ C (Phase 3, polish) labels are the second-tier amendments. See
`workspaces/engagement-survey/04-validate/07-redteam-synthesis.md`
for the full enumeration.

## Cache + DataFlow gotchas

**DataFlow returns stale results for multi-key filters on recently-
created records.** The express-mode + Redis + node-level caches all
return stale rows for 1-3s after insert. The workaround in
`services/dataflow_crud.py`: when `cache_ttl=0` is requested, route
through `_list_records_direct_sql()` which uses direct psycopg2
SQL bypass. ALWAYS pass `cache_ttl=0` from the engagement router
when freshness matters (just-launched survey, just-submitted
response).

**SQL identifier validation is mandatory** (B1):
`_validate_sql_identifier()` checks the regex
`^[a-zA-Z_][a-zA-Z0-9_]*$` before any f-string interpolation. The
direct-SQL bypass uses `_model_to_table()` which goes through this
validator. Never bypass it.

## Manager view depth checklist (P51)

When extending or building any team-aggregate view:

- [ ] **Headline** — avg + n
- [ ] **Per-dimension breakdown** — sorted ascending, top 5 lowest
      with green/amber/rose score bars (`avg < 3` rose, `< 4`
      amber, else emerald)
- [ ] **Temporal trend** — 6-pulse SVG line chart with delta label,
      respects same anonymity scope as the headline aggregate
- [ ] **Theme distribution** — chips with `theme ×count`

The `_compute_manager_trend` helper in
`engagement_surveys.py:1903` is the canonical implementation —
re-use it rather than re-deriving the per-pulse scope filter.

## Form UX baseline (P53 + post-walk polish)

- [ ] Progress counter "X of N answered" + animated bar (`aria-live`
      polite) above the form
- [ ] Sticky submit footer + form `pb-32` so footer never overlaps
      the bottom question row
- [ ] Privacy banner copy must match rendered controls — use
      `templateHasFreeText(sections)` to gate the free-text caveat
- [ ] Submit button disabled with help text ("X more questions to
      answer") rather than silently disabled (P43 in
      `security-patterns.md`)
- [ ] Thank-you page restates the privacy guarantee in the past
      tense ("HR sees aggregated trends — never individual
      responses for pseudonymous or anonymous surveys")

## Demo seed contract

`scripts/backfill_demo_engagement_surveys.py` is the canonical
demo. Two rules from the post-walk polish (P52 + general seeding):

1. **Idempotency check skips when ≥6 surveys exist.** To re-run
   after logic changes, wipe first:

   ```sql
   DELETE FROM engagement_actions WHERE company_id=1;
   DELETE FROM engagement_survey_responses WHERE company_id=1;
   DELETE FROM engagement_surveys WHERE company_id=1;
   ```

   Then re-run the seed inside the backend container (the script
   isn't baked into the image — copy it in via `docker cp`).

2. **Theme distribution must be probability-weighted, not
   categorical.** Focal themes (growth, manager) at 70-90% / 25%
   / 8% by department band; background themes (workload,
   recognition, communication, compensation, autonomy) at 5-15%
   each. See P52 in `security-patterns.md`.

## Common task recipes

### Adding a new question type to the response form

1. Add to `SurveyQuestion["type"]` union in `engagement.ts`.
2. Add a new `case` in the `QuestionRenderer` switch in `respond/page.tsx`.
3. Update `parseSections` if the question shape needs decoding.
4. If free-text, ensure `templateHasFreeText` recognises it.
5. Update `theme_tagger.py` if the new field should feed theme tagging.
6. Update `_build_aggregate` if it should be reflected in
   per-question / overall stats.

### Adding a new anonymity tier

Don't. Three tiers cover the entire privacy space (full visibility,
trend-trackable, no trail). A fourth tier creates more confusion than
clarity. If you have a new use case, model it as a metadata flag on
top of the existing tiers (e.g. "delegated re-identification by
EAP counsellor only" — that's an access-control rule, not a
fourth tier).

### Adding a new template

1. Define `sections` JSON in `engagement_library.py`.
2. Lazy-seeding: the library only seeds Q12 + monthly_pulse on first
   call when 0 templates exist. To add a new template after
   templates already exist, INSERT directly via SQL or call the
   `create_template` API.
3. If the template uses non-Likert questions, verify
   `_build_aggregate` and `_compute_manager_trend` handle the
   shape gracefully (skip non-Likert, don't crash).

### Debugging "why isn't the trend hero showing N points?"

1. `/team/aggregate` with `survey_id=0` selects the latest closed
   survey. Check the survey actually has `closed_at` set.
2. The trend skips pulses where `n < MIN_COHORT_SIZE`. A "missing"
   pulse usually means n=0/1/2/3/4 (small team + self-exclusion).
3. Anonymous-tier pulses are skipped entirely from manager trend
   (no per-team attribution possible).
4. The pseudonym lookup is per-(company, employee, survey). If you
   re-seeded mid-session, the pseudonyms changed — old responses
   no longer match the recomputed pseudonym.

## Related skills

- `security-patterns.md` — P33 (anonymity collapse), P34 (no-PII
  derived views), P49 (role-vs-capability gating), P50 (privacy
  asymmetry), P51 (aggregate view depth), P52 (seed realism), P53
  (conditional copy)
- `role-aware-ux.md` — RBAC inventory; manager view is a
  capability gate (not role gate, see P49)
- `auth-security.md` — JWT, tenant isolation, PDPA logging
- `lifecycle-dashboard.md` — Cox stage map; engagement is the
  "Stay" stage signal source
- `enrichment-and-detail-patterns.md` — pattern of resolving
  internal IDs to human names (`_resolve_employee_names`)

## Related agents

- `arbor-web-specialist` — frontend (Next.js)
- `arbor-platform-specialist` — overall router/middleware
- `trust-governance-specialist` — privacy tiers, EATP lineage
- `sg-employment-law-expert` — action templates were sg-employment-
  law-expert reviewed for SG context
