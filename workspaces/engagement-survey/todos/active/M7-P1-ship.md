# M7 — P1 ship

**Source plan:** `02-plans/03-frontend-and-phasing.md` §P1 — minimum
shippable demo + §Quality gates per phase.

The first deploy. Everything in M0-M6 must be green locally before
crossing this gate. Follow the audit discipline codified in
`.claude/agents/project/arbor-web-specialist.md` §Audit Discipline.

## T70 — Local validation pass

- **Backend:** `pytest tests/regression/test_engagement_*.py
tests/regression/test_survey_tokens.py
tests/regression/test_cohort_resolver.py
tests/regression/test_engagement_pseudonym.py
tests/regression/test_theme_tagger.py
tests/regression/test_engagement_in_app_submit.py
tests/regression/test_engagement_manager_view.py
tests/regression/test_engagement_actions.py
tests/regression/test_engagement_trend.py
tests/regression/test_engagement_loop_closing.py
tests/regression/test_engagement_suggested_actions.py` — every new test green.
- **Backend regression:** also re-run touched-area tests
  (`pytest -k "exit or appraisal or onboarding"`) to confirm the
  M0 token / theme-tagger refactor didn't drift behaviour.
- **Frontend:** `cd apps/web && npx tsc --noEmit` — clean.
- **Frontend lint:** `cd apps/web && npx eslint .` — clean (or no
  new warnings).
- **Static grep:** confirm no new raw-ID leaks (per
  `enrichment-and-detail-patterns.md`):
  ```bash
  grep -rEn '#\$\{[^}]+_id\}' apps/web/src/app/\(dashboard\)/engagement/
  grep -rEn '#\$\{[^}]+_id\}' apps/web/src/app/\(dashboard\)/my-engagement-surveys/
  ```

## T71 — Local end-to-end walk (round-3 expanded)

- **What:** Run dev frontend + backend + DB locally; walk Grace + Lily + Tanaka (manager) through the killer flow with seeded demo data.
- **Validate the brief's success criteria:**
  - Grace launches Q12 to all 28 employees in ≤3 minutes.
  - Lily completes a pulse in ≤90 seconds (in-app only — no public route at v1).
  - Aggregate appears within 30s of last response.
  - **Trend hero shows 6 prior pulses with seeded descending Engineering line.**
  - **Action panel surfaces 3 suggestions; accept-and-create-goal end-to-end works.**
  - **Loop-closing card on Lily's `/my-engagement-surveys` shows "growth → L&D pilot" action.**
  - **Manager-view as Tanaka shows aggregate; manager-of-3 sees suppression notice.**
  - eNPS hero on lifecycle dashboard shows engagement score (deferred to P2 if cross-stage panel ships there).

## T72 — Pre-deploy security review

- **Per agents.md Rule 2:** invoke `security-reviewer` on the diff.
- **Specific things to check (round-3 revised):**
  - Token kind isolation (T01) — exit token reserved; engagement-kind not minted at v1.
  - Pseudonym secret never exposed in any API response or log.
  - Admin endpoints all require role check.
  - **Manager-view endpoint enforces n≥5 + self-exclusion** (Z26).
  - **In-app submit has CSRF + Idempotency-Key** (Z11, Z08).
  - **Action endpoints have whitelist + role check.**
  - PII-clean error envelopes on submit (Z13).
  - Rate limits applied per the plan (no public engagement endpoints to limit).
  - PDPA consent_notice_version persisted.
  - **PDPA admin-access log wired into every endpoint exposing employee_id** (Z16).
  - `response_cohort_attributes` populated before identity stripping (Z03).
  - No secrets in code or .env.example.
- **Block release** on any CRITICAL finding; fix and re-review.

## T73 — Bundled deploy

- **Single commit** with the entire P1 work bundled. Conventional
  message:

  ```
  feat(engagement): P1 — templates + cohorts + launch + in-app + trend + manager-view + action-loop

  Backend: 6 DataFlow models (incl. EngagementAction) + 1 router
  + 5 helper services + 11 regression test files.
  Endpoints: /surveys/launch, /my-pending, /my-history,
  /my-responses/{id}/render+/submit, /surveys/trend,
  /team/aggregate, /surveys/{id}/suggested-actions,
  /surveys/{id}/actions, /actions, /my-loop-closing.
  Frontend: HR /engagement (trend hero + 3 tabs + wizard
  + detail with action panel), /engagement/team manager-view,
  employee /my-engagement-surveys (loop-closing card +
  in-app form, no public route) + /my-dashboard card.
  Demo: backfill_demo_engagement_surveys.py seeds 2 templates,
  6 prior pulses (trend), 1 open pulse, 1 accepted action +
  linked goal — exit-themed Likert distributions ready for
  the P2 cross-stage demo.
  ```

- **Push:** `git push origin main` (only — never to upstream per the
  user's `feedback_no_upstream`).
- **Server pull + rebuild:** standard SSH-based pattern from
  `feedback_deployment.md`. Backend AND frontend (backend has new
  models so MUST rebuild).
- **Run migration on server:** `docker exec arbor-backend python
-m alembic upgrade head` (or DataFlow equivalent).
- **Run demo seed on server:** `docker exec arbor-backend python
scripts/backfill_demo_engagement_surveys.py`. Idempotent.
- **Wait for `/api/health` 200.**

## T74 — Live verification (post-deploy, round-3 expanded)

- **Walk as Grace** — open `/engagement`, **verify trend hero renders 6 pulses**, launch a survey, verify detail page populates, scroll to action panel, accept a suggestion + create a goal.
- **Walk as Lily** — submit the launched pulse via in-app (no public route at v1). Verify loop-closing card on `/my-engagement-surveys` shows the seeded action.
- **Walk as Tanaka (manager of Engineering)** — open `/engagement/team`, verify aggregate visible (n=6). Verify a manager-of-3 sees suppression notice.
- **Run leak detector** (per `enrichment-and-detail-patterns.md` §A.4) on every engagement page.
- **Capture screenshots** into `workspaces/engagement-survey/04-validate/r1-fixed-*.png` as post-deploy audit-trail artefact (per round-3-7 protocol).

## T75 — Triage live findings

- **What:** every finding from T74 → severity (H/M/L) → fix in a
  follow-up commit OR defer to M8/M9 if non-blocking.
- **H tier:** must fix before declaring P1 closed. M-tier OK to
  defer with a tracked todo. L-tier rolled into M10 polish.

## Acceptance gate for M7

- All M0-M6 acceptance gates green.
- Single bundled commit shipped to prod.
- Server health 200; demo seed run; live walk closed.
- Brief's three success criteria empirically met (Grace launches
  ≤3 min; Lily completes ≤90s; aggregate ≤30s).
- No H-tier findings open.

## On-failure rollback

- Backend rollback: `ssh ... && cd /opt/arbor && git reset --hard
<prior-commit>` then `docker compose ... up -d --build backend
frontend`.
- Migration rollback: `alembic downgrade -1` (test reversibility on
  staging first per T15).
- Demo seed is idempotent; rolling back code without data rollback
  is safe (orphan tables stay but unreferenced).
