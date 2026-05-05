# Gate 1 — Deploy round-12 redteam closure to prod

**Source plan:** `02-plans/03-post-redteam-plan.md` Gate 1.
**State:** bundled commit `92f4d32` is in. Push + remote deploy + backfills are all that remain.
**Estimate:** 15–30 min including smoke walk.
**Owner-locked decisions:** B1 deferred. Deploy is scripted end-to-end.

## ~~Pre-work~~ ✅ DONE

- 17 of 18 redteam findings fixed (B1 deferred).
- 3 of 4 lap findings fixed (NEW-2 cosmetic only — see X-1 cross-cutting todo).
- Pre-existing TestReapplyCandidate fix shipped in passing.
- Bundled commit `92f4d32` written.

## Active

### G1-1 — Run `./deploy/ship-redteam-round-12.sh`

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

### G1-2 — Post-deploy: hand off Gate 1 to owner for B1 toggle

- **What:** Owner sets `DEFAULT_LLM_MODEL` in `deploy/.env.prod` and
  restarts the backend container when ready.
- **Recommended:** `claude-3-5-haiku-latest` — keys already in env.
- **Acceptance:** `/advisory` answers a CPF question without a red
  escalation banner. Tracked separately because it's not in this commit.

## Done when

- All Gate 1 tasks above marked complete with evidence.
- This file moves to `todos/completed/G1-deploy-redteam-round-12.md`.
- The next gate (`P1-lifecycle-dashboard`) is unblocked.
