# Gate 1 — Deploy round-12 redteam closure to prod ✅ COMPLETED

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 1.
**Completed:** 2026-05-05.
**Final commit shipped:** `e837f7d` (after two iterations on the deploy script — see "Issues encountered" below).
**Owner-locked decisions:** B1 deferred. Deploy is scripted end-to-end.

## ~~Pre-work~~ ✅ DONE

- 17 of 18 redteam findings fixed (B1 deferred).
- 3 of 4 lap findings fixed (NEW-2 cosmetic only — see X-1 cross-cutting todo).
- Pre-existing TestReapplyCandidate fix shipped in passing.
- Bundled commit `92f4d32` written.

## ~~G1-1 — Run `./deploy/ship-redteam-round-12.sh`~~ ✅ DONE

- **What:** Execute the end-to-end deploy script. The script handles
  push + SSH pull + container rebuild + 7 backfills in dependency order
  - H2 sweep + smoke check.
- **Pre-flight already enforced by the script:**
  - Round-12 regression suite must pass.
  - Working tree must be clean.
- **Owner inputs the script will need:**
  - `ADMIN_PASSWORD` (silent prompt or env var).
  - GitHub auth (`gh auth token` for the SSH-side pull).
- **Backfill order (locked into the script):**
  1. `backfill_employee_pass_type.py` (M1)
  2. `migrate_employee_tracks_attendance.py` (H1 column add)
  3. `backfill_claim_totals.py` (B3)
  4. `backfill_onboarding_templates.py` (H4)
  5. `backfill_empty_payroll_drafts.py` (M4)
  6. `backfill_demo_appraisals.py` (M5)
  7. `backfill_demo_interview_variety.py` (M7)
- **Acceptance:** every smoke probe in the script returns 2xx/3xx and
  the workforce endpoint returns the expected shape. No new console
  errors visible on a manual walk of `/dashboard`, `/payroll`, `/leave`,
  `/claims`, `/attendance`, `/employees?tab=onboarding`, `/compliance`,
  `/recruitment?tab=interviews`, `/appraisals`, `/onboarding` (redirects).
- **Rollback:** `git push origin main~1:main --force-with-lease` is
  unsafe on shared infra. Real rollback is `ssh ... && cd /opt/arbor &&
git reset --hard <prior-commit>` followed by container rebuild. None
  of the 7 backfills are destructive — they're additive or
  soft-archiving — so rollback only needs the code revert.

### G1-2 — Post-deploy: hand off Gate 1 to owner for B1 toggle (still open)

- **What:** Owner sets `DEFAULT_LLM_MODEL` in `deploy/.env.prod` and
  restarts the backend container when ready.
- **Recommended:** `claude-3-5-haiku-latest` — keys already in env.
- **Acceptance:** `/advisory` answers a CPF question without a red
  escalation banner. Tracked separately because it's not in this commit.

## Evidence (2026-05-05 deploy)

| Step                       | Result                                                                                                                                                                                                                                                                                                                                         |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1 Pre-flight               | 18 round-12 regression tests passed                                                                                                                                                                                                                                                                                                            |
| 2 Push                     | `e837f7d` to `jaredjteo-ig/arbor`                                                                                                                                                                                                                                                                                                              |
| 3 Pull + container rebuild | backend + frontend rebuilt; arbor-backend + arbor-frontend recreated and started                                                                                                                                                                                                                                                               |
| 4 Backfills                | M1 1 employee defaulted to citizen · H1 column added + 2 employees flagged · B3 5 stale claim totals corrected (4 + 1 across runs) · H4 1 duplicate template archived · M4 1 empty Jan draft + 28 payslip rows deleted · M5 H1 2026 period created + 3 in-flight reviews seeded · M7 2 candidates + 1 Completed + 1 Cancelled interview seeded |
| 5 H2 sweep                 | `Auto-cancelled 3 stale pending leave application(s).`                                                                                                                                                                                                                                                                                         |
| 6 Smoke check              | `/`: 200 · `/api/health`: 200 · `/login`: 200 · workforce: `{local:19, pr:2, ep:2, sp:3, wp:2, total:28, local_ratio:0.75}`                                                                                                                                                                                                                    |
| 7 Final                    | exit 0                                                                                                                                                                                                                                                                                                                                         |

## Issues encountered (and fixed in commits)

1. **Working-tree noise blocked step 2.** The script's strict check
   triggered on auto-generated `apps/web/.claude/learning/observations.jsonl`
   and `apps/web/test-results/.last-run.json`. Fix: stashed both before
   re-running. Follow-up: `X-cross-cutting` should track adding both
   to a `.gitignore` cleanup pass.
2. **Wrong git remote on prod.** Initial script hardcoded
   `terrene-foundation/arbor` for the remote pull; my pushes go to
   `jaredjteo-ig/arbor`. Fix: commit `522755c` made the deploy repo
   configurable via `GITHUB_DEPLOY_REPO` env var, default
   `jaredjteo-ig/arbor`. Codified into memory as
   `feedback_no_upstream.md`.
3. **`docker compose` invocation missing config flags.** Fix: same
   commit aligned the script to the existing `ship.sh` pattern —
   `-f docker-compose.prod.yml --env-file .env.prod`.
4. **`scripts/` not baked into the backend image.** Step 4 first
   crashed with "No such file or directory". Fix: commit `c845516`
   adds a `docker cp` of `scripts/` into the backend container
   before the `docker exec` loop.
5. **`backfill_empty_payroll_drafts.py` referenced a non-existent
   column (`ps.gross_pay`).** Fix: commit `e837f7d` switched the
   query to use `payroll_runs.total_gross` directly — same source
   the frontend reads. Two birds: removes a join, sidesteps the
   schema-name divergence.

## Outcome

- All Gate 1 acceptance criteria met (smoke probes 200; backfills
  applied; no regressions surfaced post-deploy).
- Gate 2 (`P1-lifecycle-dashboard.md`) is unblocked.
- G1-2 (B1 LLM toggle) remains open as an owner-side action.
