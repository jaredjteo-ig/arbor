# Ricoh Thailand Demo — Completed Milestones (M1–M6)

**Completed**: 2026-03-28 → 2026-04-01 (across multiple sessions)
**Original Objective**: Deploy Arbor as standalone commercial demo at central.kailash.ai for Ricoh Thailand CCO meeting.

---

## M1: Gemini API Migration — COMPLETE

**Approach chosen**: OpenAI-compatible endpoint (not LiteLLM, not Direct Gemini SDK).
**Commit**: `dc78a1a` — `feat(llm): migrate from OpenAI to Google Gemini via OpenAI-compatible endpoint`

| Todo | Description                       | Status                                                                    |
| ---- | --------------------------------- | ------------------------------------------------------------------------- |
| T001 | Investigate Kaizen Gemini support | DONE — Kaizen patched to route through OpenAI-compatible endpoint         |
| T002 | LiteLLM abstraction               | SKIPPED — OpenAI-compatible endpoint chosen instead (simpler, fewer deps) |
| T003 | Advisory engine function calling  | DONE — `advisory_engine.py` uses `gemini-2.5-flash` via OpenAI SDK        |
| T004 | Intent classifier                 | DONE — `intent_classifier.py` Gemini-first with OpenAI fallback           |
| T005 | Guardrails scope classification   | DONE — `guardrails.py` Gemini-first                                       |
| T006 | Response synthesizer fallback     | DONE — `response_synthesizer.py` Gemini-first                             |
| T007 | Embedding model switch            | DONE — `text-embedding-004`, 768 dimensions                               |
| T008 | Env var defaults                  | DONE — `GOOGLE_API_KEY` primary, OpenAI optional                          |
| T009 | Kaizen config patch               | DONE — Routes Gemini through OpenAI-compatible endpoint                   |
| T010 | E2E Gemini integration test       | DONE — Advisory flow verified on Gemini                                   |

---

## M2: Infrastructure & Deployment — COMPLETE

**Change from plan**: AWS EC2 (ap-southeast-1) instead of GCP. Domain: `central.kailash.ai`.
**Commit**: `434acf9` — `feat(deploy): switch to AWS EC2 deployment at central.kailash.ai`

| Todo | Description        | Status                                                  |
| ---- | ------------------ | ------------------------------------------------------- |
| T011 | Provision instance | DONE — AWS EC2 t3.medium, ap-southeast-1                |
| T012 | Domain + DNS       | DONE — central.kailash.ai with Caddy SSL                |
| T013 | Deployment config  | DONE — ship.sh, Caddyfile, docker-compose updated       |
| T014 | Production .env    | DONE — Gemini keys, JWT, CORS configured                |
| T015 | Deploy + verify    | DONE — Health checks passing                            |
| T016 | Fresh DB + KB load | DONE — Tables created, KB loaded with Gemini embeddings |

---

## M3: Branding & Data Cleanup — COMPLETE

**Commit**: `f21511c` — `refactor(brand): rebrand Arbor to Central across all user-facing surfaces`

| Todo | Description             | Status                                                              |
| ---- | ----------------------- | ------------------------------------------------------------------- |
| T017 | AITE branding remnants  | DONE — All references removed                                       |
| T018 | Metadata descriptions   | DONE — "Central — HR Advisory" across web/mobile/pyproject          |
| T019 | Email domains           | DONE — @arbor.terrene.dev                                           |
| T020 | Demo seed script        | DONE — `scripts/seed_demo_data.py` with "Central Solutions Pte Ltd" |
| T021 | Demo company LLM budget | DONE — Configurable via seed script                                 |

---

## M4: UX Demo Polish — COMPLETE

**Commits**: Various across `b978a47` and prior sessions.

| Todo | Description            | Status                                           |
| ---- | ---------------------- | ------------------------------------------------ |
| T022 | Date picker            | DONE — `DatePicker.tsx` with calendar popover    |
| T023 | Employee search picker | DONE — `EmployeePicker.tsx` with type-ahead      |
| T024 | Reports charts         | DONE — Bar, donut, trend charts (pure CSS/SVG)   |
| T025 | Dashboard enhancement  | DONE — Metric cards, compliance, shadow briefing |
| T026 | Clients page           | DONE — Full CRUD with search/filtering           |

---

## M5: Demo Data & Testing — PARTIAL

| Todo | Description                   | Status                                          |
| ---- | ----------------------------- | ----------------------------------------------- |
| T027 | Pre-test 5 scripted questions | NOT RUN — Requires live deployment verification |
| T028 | Smoke test script             | DONE — `scripts/demo_smoke_test.py`             |
| T029 | Conversation persistence      | NOT TESTED — Manual test post-deployment        |
| T030 | Latency measurement           | NOT DOCUMENTED — Manual profiling needed        |

---

## M6: Demo Materials & Narrative — COMPLETE

All materials in `01-analysis/01-research/`.

| Todo | Description          | Status                                          |
| ---- | -------------------- | ----------------------------------------------- |
| T031 | CCO narrative        | DONE — `10-ricoh-thailand-proposal-analysis.md` |
| T032 | Leave-behind brief   | DONE — `08-leave-behind-brief.md`               |
| T033 | ChatGPT comparison   | DONE — `06-chatgpt-comparison.md`               |
| T034 | Architecture diagram | DONE — `07-architecture-diagram.md`             |
| T035 | Backup demo video    | NOT RECORDED — Operational task                 |

---

## M7: Demo Resilience — OBSOLETE

Demo date (2026-03-28) has passed. These were demo-day operational tasks.

| Todo | Description          | Status                                                        |
| ---- | -------------------- | ------------------------------------------------------------- |
| T036 | Pre-warming protocol | OBSOLETE                                                      |
| T037 | Fallback plan        | OBSOLETE — Partial coverage in `04-critical-demo-warnings.md` |
| T038 | BYOK backup key      | OBSOLETE                                                      |
