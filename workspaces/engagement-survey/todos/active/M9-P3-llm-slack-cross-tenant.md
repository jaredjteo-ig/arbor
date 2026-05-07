# M9 — P3: LLM theme analysis + Slack/Teams

**Round-3+ revision (2026-05-07):** Cross-tenant comparison (T97) + cross-tenant settings page (T98) DROPPED — owner's deployment model is one company per server, so cross-tenant aggregation has no use case. P3 narrows to LLM theme analysis + Slack/Teams delivery + LLM-richer action suggestions.

**Source plan:** `02-plans/03-frontend-and-phasing.md` §P3 — AI +
integrations, plus `02-plans/04-product-revision-round3.md` (manager
view + cross-stage correlation moved out of P3 to P1/P2 respectively).

P3 narrows. The cross-stage USP demo flow ships at P2; P3 layers the
AI + integration capabilities on top. Cross-tenant comparison is the
last addition — anonymised median benchmarks for sector peers who
opted in.

## T94 — LLM theme analysis (gated by P13 cost cap)

- **What:** Replace the deterministic `_theme_tags` (T05) with an LLM-driven theme clusterer for engagement responses.
- **Trigger:** after a survey closes, batch-process all submitted responses through the existing advisory engine with a theme-extraction signature.
- **Cost guard (P13):** per-survey ceiling of 100 LLM calls; if survey has >100 responses, sample 100 representative responses (stratified by Likert score). Per-tenant per-day cost cap on top.
- **Storage:** save derived themes onto each `EngagementSurveyResponse.themes` (overwriting the deterministic tags). Keep deterministic tags as `themes_v1` for trend continuity if needed.
- **Failure mode:** on LLM error, fall back to deterministic tagger silently. No demo blocker.
- **Acceptance:** themes richer + more specific than keyword sweep; budget cap enforced; deterministic fallback exercised by unit test that injects an LLM error.

## T95 — Slack / Teams delivery

- **What:** When launching a survey, optionally deliver via Slack or Teams. Small button at step 3 of launch wizard. Opt-in per launch.
- **Implementation:** webhook adapter under existing MCP integrations layer (`mcp-integrations.md`). Per-company OAuth-scoped token for the workspace.
- **Per-employee DM contains:**
  - Loop-closing context: "Last pulse, your team raised growth — HR launched a learning budget pilot. New pulse asks how that's going."
  - Direct link to `/my-engagement-surveys/{response_id}/respond` (still in-app — Slack doesn't replace the in-app form).
- **Channel announcement:** in HR channel, "{n} responses sent for {survey_name}, closes {date}."
- **Acceptance:** Grace launches a pulse with Slack opt-in; HR channel receives announcement; per-employee DMs deliver. Click-through lands on in-app form.

## T96 — Action panel: LLM action suggestions become richer

- **What:** P1 ships deterministic suggested-action templates (M3 T36) + light Kaizen call. P3 upgrades this to a richer Kaizen-driven flow that:
  - Reads the last 6 pulses' themes.
  - Reads any prior accepted actions for similar themes.
  - Suggests time-bound, measurable actions tailored to the cohort's tenure / size / stage.
- **Cost cap:** same P13 ceiling as T94.
- **Acceptance:** suggestion quality measurably improves over P1 deterministic; user-facing measure: HR accept-rate of P3 suggestions vs P1 baseline.

## T97 — DROPPED (no multi-tenant deployment)

## T98 — DROPPED (no multi-tenant deployment)

## T99 — P3 ship

- Same shape as M7 / M8 — pre-flight, security review, single bundled commit, server pull + rebuild, live walk.
- **Walk:** Slack delivery; Cross-tenant median visible if seeded with simulated peer data; LLM theme analysis on a closed survey.
- **Acceptance:** P3 ships green; the three new capabilities each demo'd.

## Removed from M9 (moved earlier)

- ~~Cross-stage correlation~~ → M8 T87.
- ~~Lifecycle leading-indicator panel~~ → M8 T88.
- ~~Lifecycle activity-feed entries~~ → M8 T89.
- ~~eNPS hero on lifecycle dashboard~~ → M8 T90.
- ~~Manager view~~ → M3 T35 + M4 (P1).

## Dependencies

- T94 ← advisory engine + P13 budget cap.
- T95 ← MCP integrations layer + existing OAuth flow.
- T96 ← T94 (LLM available).
- T97, T98 ← `Company.industry_sector` + opt-in setting persistence.
- T99 ← all of the above.

## Acceptance gate for M9

- LLM theme analysis runs and falls back deterministically.
- Slack delivery works.
- Richer LLM-driven action suggestions ship over P1's deterministic baseline.
- All P3 features demo'able end-to-end.
