# Cluster 7A — T-R054: AI Candidate Scorecards (Kaizen)

**Status:** Complete
**Owner:** Kaizen specialist agent
**Test result:** `tests/unit/test_scorecard_agent.py` — 12 passed in 0.45s

## Goal

When an interviewer requests a scorecard for a candidate, a Kaizen
agent reads the candidate profile, the relevant job listing's
requirements, and any interview feedback collected so far, and
generates a structured scorecard with: overall fit (1-5), per-
competency ratings, strengths, concerns, and a recommended decision
(`proceed` / `reject` / `further_interview`).

## What changed

### Backend

- **NEW** `src/hr_advisory/agents/scorecard_agent.py`
  - `ScorecardSignature` (Kaizen `Signature` subclass) with inputs
    `candidate_profile`, `job_listing`, `scorecard_template`,
    `interview_feedback`, and outputs `overall_fit`,
    `competency_ratings`, `strengths`, `concerns`,
    `recommended_decision`, `narrative`.
  - `ScorecardAgentConfig` dataclass, auto-resolves provider+model via
    `resolve_provider_and_model()` — no hardcoded model strings;
    flows through `DEFAULT_LLM_MODEL` / Settings / BYOK overrides.
  - `ScorecardAgent(BaseAgent)` with `generate(...)` returning
    `{scorecard, degraded}`.
  - System prompt explicitly forbids referencing protected attributes
    (race, religion, age, family status, gender, nationality,
    disability) and forbids inventing qualifications.
  - Hardening:
    - Ratings clamped to 1–5; non-template criterion keys ignored.
    - Decision constrained to `VALID_DECISIONS`; defaults to
      `further_interview` on invalid LLM output.
    - LLM exceptions caught and returned as a fallback scorecard
      with `degraded=True` rather than 500-ing the caller.
    - `criteria` field accepts both list and JSON-string forms (the
      DB stores JSON-string; the agent normalises).
- **UPDATED** `src/hr_advisory/agents/__init__.py` — re-exports
  `ScorecardAgent`, `ScorecardAgentConfig`, `ScorecardSignature`.
- **UPDATED** `src/hr_advisory/api/routers/recruitment.py` —
  appended one new endpoint at the end of the file. Existing
  endpoints untouched:
  - `POST /recruitment/candidates/{candidate_id}/scorecard/generate`
  - Auth: `require_role("owner", "hr_manager")`
  - Rate limit: 10 req / 60 s / user via `check_rate_limit`
  - Body: `{template_id: int}`
  - Loads candidate + job listing + `InterviewFeedback` rows,
    enforces tenant isolation on every record, calls the agent.
  - Persists the AI scorecard as a `ScorecardEntry` row with
    `is_ai_generated=True`, `generation_id`, structured `notes`
    JSON, `total_score = overall_fit`. Wrapped in try/except so the
    endpoint still returns useful output if the schema lacks the
    AI-only columns (no migrations are run by this task).
  - Logs an audit-trail line via `_log_candidate_activity`.
  - Lazy-imports the agent so the rest of the recruitment router
    keeps importing even if Kaizen extras are missing.

### Frontend

- **REWROTE** `apps/web/src/app/(dashboard)/recruitment/candidates/[id]/page.tsx`
  - Was a redirect stub. Now hosts the candidate detail header and
    the AI Scorecard card.
  - "Generate AI Scorecard" button is gated on the
    `arbor.ai-scorecards` localStorage flag — disabled message
    points to Recruitment Settings when off.
  - Loads scorecard templates via existing
    `recruitmentApi.listScorecardTemplates`.
  - On click, calls the new `recruitmentApi.generateAIScorecard`,
    renders overall fit, per-criterion ratings (with weights),
    strengths, concerns, decision, and narrative.
  - Surfaces `degraded=true` as an amber "reduced confidence" hint.
- **UPDATED** `apps/web/src/app/(dashboard)/recruitment/settings/page.tsx`
  - Added `AiScorecardToggle` section next to the existing TAFEP
    `AiScanToggle`. localStorage key: `arbor.ai-scorecards`.
- **UPDATED** `apps/web/src/services/api/recruitment.ts`
  - Added `generateAIScorecard(candidateId, {template_id})` with a
    fully-typed response shape (`scorecard`, `generation_id`,
    `degraded`, `persisted_entry_id`).

### Tests

- **NEW** `tests/unit/test_scorecard_agent.py` — 12 tests, all pass
  in well under a second. Covers:
  - Initialisation (config, signature, system prompt rules).
  - Happy path — structured dict shape, JSON-serialised inputs to
    `run`, default empty feedback.
  - Resilience — invalid decisions, unparseable overall_fit,
    out-of-range and unknown ratings, LLM exceptions, JSON-string
    criteria.
  - LLM is mocked via `patch.object(agent, "run", ...)` and the
    `extract_*` helpers; no real API calls.

## Files touched

```
src/hr_advisory/agents/scorecard_agent.py            (new)
src/hr_advisory/agents/__init__.py                   (re-export)
src/hr_advisory/api/routers/recruitment.py           (1 new endpoint appended)
apps/web/src/app/(dashboard)/recruitment/candidates/[id]/page.tsx  (full page)
apps/web/src/app/(dashboard)/recruitment/settings/page.tsx          (toggle added)
apps/web/src/services/api/recruitment.ts             (1 method added)
tests/unit/test_scorecard_agent.py                   (new)
```

No changes to `models/company_user.py`, no Alembic migrations, no
DataFlow model edits.

## How to verify

```bash
.venv/bin/python -m pytest tests/unit/test_scorecard_agent.py -x -q
```

Expected: `12 passed`.

## Notes for follow-up clusters

- Persistence currently uses the existing `ScorecardEntry` table
  with `is_ai_generated`/`generation_id` written best-effort; if
  the deployed schema lacks those columns the API still returns
  the scorecard plus a transient `generation_id`. A future
  migration can add the columns and back-fill is_ai_generated=False
  on existing rows.
- The candidate detail page only shows a minimal header + AI
  scorecard card — resume preview, activity timeline, and feedback
  list are still tracked elsewhere in the recruitment backlog.
