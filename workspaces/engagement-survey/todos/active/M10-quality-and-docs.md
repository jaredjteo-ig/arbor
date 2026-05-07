# M10 — Quality + docs + codify

**Source plan:** end-of-project hardening. Runs after P1/P2/P3 are
live. Closes the COC five-layer loop (codify the patterns we learned
into reusable knowledge artefacts).

## T100 — Pre-existing-failures audit

- **What:** Per `.claude/rules/zero-tolerance.md` Rule 1 ("if you
  found it, you own it"). Run the full pytest suite and triage any
  pre-existing failures touched by the engagement-survey work.
- **Specifically watch for:** the async-pool teardown flakes
  documented in `04-validate/03-redteam-findings-round3.md` of the
  obayashi workspace — these may surface again after migration.
- **Acceptance:** every test fixed OR documented as pre-existing
  with a tracked issue.

## T101 — Update API documentation

- **What:** Add the engagement-survey routes to `docs/02-api-reference.md`
  (or wherever the OpenAPI/MkDocs reference lives).
- **Per `rules/documentation.md`:** version numbers in docs match
  pyproject.toml; no internal domain references; URLs point at
  `terrene-foundation/kailash-py`.
- **Acceptance:** Sphinx build (`cd docs && python build_docs.py`)
  succeeds; new endpoints appear in the API reference.

## T102 — Update CLAUDE.md project context

- **What:** Add engagement-surveys to the "30+ FastAPI routers"
  inventory line in `.claude/skills/project/SKILL.md` Quick
  Reference; mention the new module in `CLAUDE.md` if it lists
  modules.
- **Acceptance:** new sessions discover the engagement module on
  load; project-overview docs are accurate.

## T103 — Codify patterns learned

Per the COC discipline (rounds 3-7 closed with /codify producing
P40-P48 + 2 new skill files in obayashi), the engagement-survey work
will surface its own patterns. Likely candidates:

- **PXX — Anonymity-tier pattern:** identified / pseudonymous /
  anonymous as a three-tier choice; HMAC pseudonym for cross-survey
  trends without re-identification. The matching shape for any
  future survey-style feature.
- **PXX — Template snapshot at launch:** the C3 fix shape — when a
  template is referenced by an immutable instance, snapshot the
  template body onto the instance to defend against post-launch
  edits.
- **PXX — Cohort fan-out + termination sweep:** when a cohort is
  resolved at launch and rows are pre-created, terminations during
  the open window must void the rows.
- **PXX — Schedule overlap protection:** cron tick must skip when
  prior instance hasn't closed.
- Generalised playbook: `surveys-platform-patterns.md` skill that
  covers all four shapes — siblings to `enrichment-and-detail-patterns.md`
  - `role-aware-ux.md`.
- **Acceptance:** new skills committed; SKILL.md index updated;
  arbor-platform-specialist agent updated with new pattern table
  rows.

## T104 — Lifecycle dashboard skill update

- **What:** Update `.claude/skills/project/lifecycle-dashboard.md`
  with the new Reward stage tile (engagement score) and the Retain
  stage cross-stage panel (M9 T91). Add the
  `lifecycle_correlation` service to the architecture diagram.
- **Acceptance:** future agents working on the lifecycle dashboard
  understand engagement is now one of its inputs.

## T105 — Update auth-security skill

- **What:** Add a row to the RBAC role-page matrix in
  `.claude/skills/project/auth-security.md` for the engagement-survey
  routes.
- **Specifically:** admin endpoints under `/engagement-surveys/**`
  require owner/hr_manager; employee endpoints under `/my-engagement-*`
  require any authenticated user; public endpoints under
  `/engagement-surveys/public/**` require token only.

## T106 — Session notes + workspace closure

- **What:** Write `.session-notes` for the engagement-survey
  workspace summarising P1/P2/P3 ship commits + open follow-ups.
- **Move all completed todos** from `todos/active/` to `todos/completed/`.
- **Update workspace `.session-notes`** for context-restore on
  the next session (per `/wrapup` skill).
- **Acceptance:** workspace is in a "done" state — todos moved,
  session-notes captured, ready for archive.

## T107 — Optional: cross-tenant aggregate (future)

- **What:** Anonymized cross-tenant comparison ("your eNPS vs the
  median across the platform's tenants in your sector"). Out of P3
  scope; logged for future planning.
- **Privacy:** requires per-tenant opt-in, k≥5 anonymity gate
  preserved across tenants, separate privacy review.

## Dependencies

T100 ← every milestone closed.
T101-T105 ← code shipped.
T103 ← `/codify` skill invoked at the end.
T106 ← `/wrapup` skill invoked at the end.

## Acceptance gate for M10

- Sphinx docs build clean with new endpoints.
- All learned patterns codified into skills + SKILL.md.
- Pre-existing failures triaged.
- Session notes written.
- Project closed.
