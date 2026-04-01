# Arbor Redeployment Analysis — Ricoh Thailand Demo

**Date**: 2026-03-24
**Objective**: Identify every code, config, and data change needed to redeploy Arbor as a clean Ricoh Thailand demo instance, switching from OpenAI to Gemini API

---

## Executive Summary

The codebase is cleaner than expected. No "TPC" references exist. The main work falls into 4 categories:

1. **Gemini API migration** — 5 files with direct OpenAI calls + embedding dimension change (HARD)
2. **Singapore-specific business logic** — 84 hardcoded instances across calculators, specialists, guardrails (HARD for Thailand, but can DEMO with Singapore content)
3. **Infrastructure config** — Domain, GCP project, email, deployment scripts (EASY)
4. **Branding/seed data** — Demo company name, AITE remnants, metadata (EASY)

**Good news**: The BYOK system already lists Gemini as a valid provider. DataFlow auto-migrates (no Alembic). Multi-tenancy is already implemented. The streaming layer is already provider-agnostic.

---

## Category 1: OpenAI to Gemini Migration

### 1.1 Architecture Status — Better Than Expected

The platform already has multi-provider infrastructure:

- `src/hr_advisory/services/llm_config.py:31` — `VALID_PROVIDERS` includes `"gemini"` already
- `apps/web/src/app/(dashboard)/settings/ai/page.tsx` — UI dropdown already lists Google Gemini
- `apps/web/src/services/api/llm-config.ts` — TypeScript type includes `"gemini"`
- `src/hr_advisory/performance/streaming.py` — SSE streaming is already provider-agnostic

### 1.2 Files Requiring Direct Code Changes

#### EASY (Config/Env — minutes)

| File                                    | Line  | Current                                          | Change To                                   |
| --------------------------------------- | ----- | ------------------------------------------------ | ------------------------------------------- |
| `.env.example`                          | 14-17 | `OPENAI_API_KEY`, `OPENAI_PROD_MODEL=gpt-5-mini` | `GEMINI_API_KEY`, model name                |
| `deploy/.env.prod.example`              | 17-19 | `OPENAI_API_KEY`, `OPENAI_PROD_MODEL`            | Gemini equivalents                          |
| `src/hr_advisory/config/settings.py`    | 32-35 | Default models `gpt-4o`, `gpt-4o-mini`           | Gemini model names                          |
| `src/hr_advisory/agents/llm_context.py` | 42    | Default provider `"openai"`                      | `"gemini"`                                  |
| `pyproject.toml`                        | 51    | `"openai>=1.30.0"` dependency                    | Add `google-generativeai` or `google-genai` |

#### MODERATE (API call pattern rewrites — hours each)

| File                                                           | Lines   | What's There                                           | What Needs To Change |
| -------------------------------------------------------------- | ------- | ------------------------------------------------------ | -------------------- |
| `src/hr_advisory/shadow/intent_classifier.py`                  | 331-354 | `openai.OpenAI()` + `client.chat.completions.create()` | Gemini SDK call      |
| `src/hr_advisory/workflows/guardrails.py`                      | 495-511 | `openai.OpenAI()` + `client.chat.completions.create()` | Gemini SDK call      |
| `src/hr_advisory/agents/orchestration/response_synthesizer.py` | 169-198 | `OpenAI()` + `client.chat.completions.create()`        | Gemini SDK call      |
| `src/hr_advisory/quality/mutation_engine.py`                   | 77      | `_call_llm()` via OpenAI                               | Gemini call          |

#### HARD (Architectural — days)

| File                                        | Lines           | Issue                                                                                                                                                                               | Complexity                                                                                    |
| ------------------------------------------- | --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `src/hr_advisory/agents/advisory_engine.py` | 28-242, 609-673 | **Function calling / tool use** — 214 lines of OpenAI tool definitions + response parsing (`choice.message.tool_calls`, `finish_reason == "tool_calls"`, `tool_call.function.name`) | Must transpile to Gemini `FunctionDeclaration` format. Different request AND response schema. |
| `src/hr_advisory/kb/embeddings.py`          | 77-84           | **Embedding model** — uses `text-embedding-3-small` (1536 dim)                                                                                                                      | Gemini `text-embedding-004` is 768 dim. ALL existing vectors must be regenerated.             |
| `src/hr_advisory/models/vector_setup.py`    | 11              | `VECTOR_DIMENSIONS = 1536`                                                                                                                                                          | Change to Gemini's dimension (768). Requires DB migration (drop and recreate HNSW index).     |
| `src/hr_advisory/agents/config.py`          | 82-138          | **Kaizen framework monkey-patch** — patches `kaizen.config.providers.get_openai_config()`                                                                                           | Must verify if Kailash Kaizen supports Gemini natively, or write new provider plugin          |

### 1.3 Recommended Approach: LiteLLM Abstraction

Rather than rewriting every OpenAI call to Gemini directly, consider inserting **LiteLLM** as a provider abstraction:

```python
# Instead of:
import openai
client = openai.OpenAI(api_key=key)
response = client.chat.completions.create(model="gpt-4o", ...)

# Use:
import litellm
response = litellm.completion(model="gemini/gemini-2.0-flash", ...)
```

LiteLLM translates OpenAI-format calls to Gemini (and 100+ other providers) automatically, including function calling. This reduces the migration from "rewrite 5 files" to "change import + model string in 5 files."

**Trade-off**: Adds a dependency but makes future provider switches trivial.

### 1.4 Embedding Migration Plan

This is unavoidable regardless of approach:

1. Change `VECTOR_DIMENSIONS` from 1536 to 768 (or whatever Gemini's model produces)
2. Drop the existing HNSW index
3. Re-embed all KB provisions using Gemini's embedding model
4. Recreate the HNSW index

For a fresh deploy with a new database, this is free — just configure the right dimension before first KB load.

---

## Category 2: Singapore-Specific Code

### 2.1 Critical Architecture Gap

**No `country` or `jurisdiction` field exists in the Company model.** The entire platform assumes Singapore. For a Thailand deployment, either:

- **Option A (Demo path)**: Deploy as-is with Singapore content, frame as "architecture demo" (the existing demo strategy)
- **Option B (Quick fork)**: Hard-swap all SG content for Thai content (breaks SG instance)
- **Option C (Proper)**: Add `jurisdiction` field to Company, parameterize all calculators and domain routing

For the Ricoh demo, **Option A is safest** — show Singapore as proof, explain Thailand adaptation. Option B if you want to show Thai provisions.

### 2.2 Hardcoded Singapore Business Logic (84 instances)

#### Calculators (6 files, ~30 instances)

| File                                              | What's Hardcoded                                                                       |
| ------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `calculators/cpf_calculator.py:26-69`             | CPF rate tables by citizenship tier + age band, OW ceiling $8,000, AW ceiling $102,000 |
| `calculators/quota_levy_calculator.py:23-99`      | DRC by sector (35%-87.5%), levy rates by pass type ($300-$950/month)                   |
| `calculators/overtime_calculator.py:39-62`        | EA Part IV salary ceiling $2,600, OT multipliers 1.5x/2.0x                             |
| `calculators/leave_calculator.py:60-131`          | Annual leave 7→14 days progression, sick leave table from EA s89                       |
| `calculators/cost_to_company_calculator.py:46-54` | SDL rate 0.25% (min $2, max $11.25), levy rates by pass type                           |
| `services/payroll_calculator.py:15-64`            | CPF ceilings duplicated, SHG contribution tables by race (CDAC, MBMF, SINDA, ECF)      |

#### Specialist Agents (8 files, ~20 instances)

| File                                     | What's Hardcoded                                                                  |
| ---------------------------------------- | --------------------------------------------------------------------------------- |
| `agents/specialists/_base.py:62`         | Base prompt: "You are a {domain} specialist for **Singapore employment matters**" |
| `agents/specialists/cpf.py`              | CPF Act domain prompt                                                             |
| `agents/specialists/employment_act.py`   | EA domain prompt                                                                  |
| `agents/specialists/foreign_manpower.py` | EFMA domain prompt                                                                |
| `agents/specialists/tax.py`              | IRAS domain prompt                                                                |
| `agents/specialists/fair_employment.py`  | TAFEP domain prompt                                                               |
| `agents/specialists/wsh.py`              | WSH Act domain prompt                                                             |
| `agents/specialists/pdpa.py`             | PDPA domain prompt                                                                |

#### Guardrails (1 file, ~10 instances)

| File                             | What's Hardcoded                                                                                                                                     |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `workflows/guardrails.py:68-109` | Circumvention patterns: "avoid paying CPF", "pay below progressive wage", "hire without permit", "fake payslip/KET" — all reference SG-specific laws |

#### Database Models (1 file, ~15 instances)

| File                     | What's Hardcoded                                                                                                                                                                                           |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `models/company_user.py` | LeaveTypeCode includes "NS" (National Service), ImmigrationStatus has PR_YEAR1/2/3+ (SG CPF tiers), PassType has EP/SP/WP (SG-specific), currency defaults to "SGD", postal code assumes 6-digit SG format |

#### Frontend (12+ files, ~15 instances)

| Location                                                           | What's Hardcoded                                                 |
| ------------------------------------------------------------------ | ---------------------------------------------------------------- |
| `apps/web/src/app/page.tsx:144-150`                                | SAMPLE_DOMAINS: "Employment Act", "CPF", "EFMA", "IRAS", "TAFEP" |
| `apps/web/src/lib/i18n/en.json:4`                                  | `"tagline": "AI-powered HR Advisory for Singapore SMEs"`         |
| `apps/web/src/components/integrations/PayNowQRModal.tsx:80`        | `currency: "SGD"`                                                |
| `apps/web/src/app/(dashboard)/training/skillsfuture/page.tsx`      | SGD currency, SkillsFuture (SG programme)                        |
| `apps/web/src/app/(dashboard)/payroll/accounting-sync/page.tsx:78` | `currency: "SGD"`                                                |

#### Mobile App (9 files, ~15 instances)

| Location                                                                 | What's Hardcoded                                                         |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| `apps/mobile/lib/features/onboarding/screens/onboarding_screen.dart:173` | "Singapore employment law"                                               |
| `apps/mobile/lib/features/advisory/screens/advisory_screen.dart:383`     | "Ask Arbor anything about Singapore HR"                                  |
| `apps/mobile/lib/features/calculators/widgets/cpf_form.dart`             | "Monthly Salary (SGD)", "Singapore Citizen" dropdown                     |
| `apps/mobile/lib/features/calculators/logic/cpf_logic.dart`              | CPF rates, "monthly wages above SGD 750"                                 |
| `apps/mobile/lib/features/calculators/logic/overtime_logic.dart`         | "Workmen: salary up to SGD 4,500", "Non-workmen: salary up to SGD 2,600" |

#### Government Integration (1 file)

| File                                    | What's Hardcoded                                           |
| --------------------------------------- | ---------------------------------------------------------- |
| `mcp_servers/adapters/myinfo.py:62-100` | MyInfo API `https://api.myinfo.gov.sg/v5`, Singpass scopes |

#### Statutory Filing (1 file)

| File                                  | What's Hardcoded                         |
| ------------------------------------- | ---------------------------------------- |
| `services/statutory_files.py:20-100+` | CPF e-Submit CSV format, IR8A generation |

---

## Category 3: Infrastructure & Deployment Config

### 3.1 Domain & Hosting (MUST change)

| File                             | Line        | Current                                                                                                 | Action          |
| -------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------- | --------------- |
| `deploy/Caddyfile`               | 1           | `arbor.terrene.foundation`                                                                              | New domain      |
| `deploy/docker-compose.prod.yml` | 36,39,58,62 | `https://arbor.terrene.foundation` (CORS, API URLs)                                                     | New domain      |
| `deploy/.env.prod.example`       | 35          | Google OAuth redirect to `arbor.terrene.foundation`                                                     | New domain      |
| `deploy/.env.prod.example`       | 40          | CORS origin `arbor.terrene.foundation`                                                                  | New domain      |
| `deploy/deployment-config.md`    | 7-60        | GCP project `terrene-care`, instance `arbor-prod`, IP `34.87.60.241`, account `jack@terrene.foundation` | New GCP project |
| `deploy/ship.sh`                 | 14-16       | `PROJECT="terrene-care"`, `ZONE="asia-southeast1-b"`, `INSTANCE="arbor-prod"`                           | New values      |

### 3.2 Email (SHOULD change)

| File                                                   | Line    | Current                                           | Action             |
| ------------------------------------------------------ | ------- | ------------------------------------------------- | ------------------ |
| `src/hr_advisory/config/settings.py`                   | 51, 120 | `noreply@arbor.sg`                                | New email domain   |
| `src/hr_advisory/mcp_servers/adapters/resend_email.py` | 254     | `Arbor HR Platform <noreply@arbor.sg>`            | New sender         |
| `src/hr_advisory/mcp_servers/adapters/ses_email.py`    | 50, 60  | `notifications@arbor.sg`, region `ap-southeast-1` | New email + region |
| `apps/web/src/app/(dashboard)/help/page.tsx`           | 334     | `mailto:support@arbor.sg`                         | New support email  |

### 3.3 Database (change via env vars)

| File                                 | Line | Current Default                                 | Action                     |
| ------------------------------------ | ---- | ----------------------------------------------- | -------------------------- |
| `src/hr_advisory/config/settings.py` | 27   | `postgresql://arbor:arbor@localhost:5432/arbor` | Set `DATABASE_URL` env var |
| `src/hr_advisory/models/database.py` | 15   | Same default                                    | Overridden by env var      |
| `docker-compose.dev.yml`             | 6-8  | `POSTGRES_USER: arbor`, `POSTGRES_DB: arbor`    | Change for prod            |

### 3.4 Frontend API URLs (already env-var driven)

8+ frontend files default to `http://localhost:8000` but all read `NEXT_PUBLIC_API_URL` at build time. Set the env var and they're fine.

---

## Category 4: Branding & Seed Data

### 4.1 AITE Remnants (4 files)

| File                                          | Line | Issue                                                            | Fix                           |
| --------------------------------------------- | ---- | ---------------------------------------------------------------- | ----------------------------- |
| `apps/mobile/lib/core/config/app_config.dart` | 10   | Comment "AITE backend API"                                       | Change to "Arbor backend API" |
| `apps/web/tests/e2e/helpers/auth.helper.ts`   | 85   | Comment "aite_app on port 8099"                                  | Update comment                |
| `tests/e2e/test_live_api_all_flows.py`        | 17   | Hardcoded path `/Users/esperie/repos/asme/aite/src`              | Fix or remove                 |
| Mobile package name                           | —    | Task T501 in roadmap: `sg.aite.hr_advisory_mobile → sg.arbor.hr` | Not yet done                  |

### 4.2 Demo Seed Data (1 file)

| File                        | Lines  | Issue                                                                 | Fix                                      |
| --------------------------- | ------ | --------------------------------------------------------------------- | ---------------------------------------- |
| `scripts/seed_demo_data.py` | 36-39  | `demo@sakura-trading.sg`, `SakuraDemo2026!`, `Sakura Trading Pte Ltd` | Make configurable or create Thai version |
| Same file                   | 47-473 | 28 employee profiles with `@sakura-trading.sg` emails                 | Update for Thai demo company             |

### 4.3 Branding Metadata

| File                          | Line  | Current                                                                     | Action             |
| ----------------------------- | ----- | --------------------------------------------------------------------------- | ------------------ |
| `apps/web/src/app/layout.tsx` | 13-14 | "Arbor — HR Advisory", "AI-powered HR advisory platform for Singapore SMEs" | Update description |
| `apps/mobile/pubspec.yaml`    | 1-2   | "AI-powered HR advisory platform for Singapore SMEs"                        | Update             |
| `pyproject.toml`              | 6-10  | Description "Singapore SMEs", author `dev@arbor.sg`                         | Update             |

---

## Category 5: Database — Fresh Deploy Plan

### 5.1 Current State

- **72 DataFlow models** across 4 model files
- **No Alembic migrations** — DataFlow `auto_migrate=True` handles everything
- **Multi-tenancy** via `company_id` on all employee-scoped tables
- **pgvector** for KB semantic search (currently 1536-dim for OpenAI embeddings)

### 5.2 Fresh Deploy Steps

```
1. Create fresh PostgreSQL 14+ database
2. Ensure pgvector extension available
3. Set DATABASE_URL, REDIS_URL env vars
4. Start application — DataFlow auto-creates all 72 tables + indexes
5. Register first user (becomes company owner)
6. Company seeding auto-creates leave policies, claim categories, etc.
7. Load KB content (Acts, Domains, Provisions)
8. Generate vector embeddings (using Gemini embedding model)
9. Run seed script for demo data (modified for Thai company)
```

### 5.3 Vector Dimension Change

If switching to Gemini embeddings:

- `vector_setup.py:11` — Change `VECTOR_DIMENSIONS = 1536` to `768`
- Fresh database means no migration needed — just set the right dimension before first load
- All KB provisions will be embedded fresh with Gemini's model

### 5.4 In-Memory Storage Risk

QA sessions and some settings are stored in-memory dicts. Server restart clears them. For demo:

- Prep demo data right before the demo, or accept fresh starts
- Advisory sessions ARE database-backed (persistent)
- Conversation threads have DB models but may not be fully wired

---

## Priority Action Plan

### P0 — Must Do (blocks deployment)

| #   | Task                                   | Files                                                                                    | Effort                    |
| --- | -------------------------------------- | ---------------------------------------------------------------------------------------- | ------------------------- |
| 1   | Create new GCP project + instance      | `deploy/ship.sh`, `deploy/deployment-config.md`                                          | 1-2 hours                 |
| 2   | Set up new domain + SSL                | `deploy/Caddyfile`, `deploy/docker-compose.prod.yml`                                     | 1 hour                    |
| 3   | Switch LLM to Gemini (env vars)        | `.env`, `settings.py`, `llm_context.py`                                                  | 30 min                    |
| 4   | Rewrite 4 direct OpenAI API calls      | `intent_classifier.py`, `guardrails.py`, `response_synthesizer.py`, `advisory_engine.py` | 2-3 days                  |
| 5   | Switch embedding model + dimension     | `embeddings.py`, `vector_setup.py`                                                       | 2 hours                   |
| 6   | Verify Kaizen framework Gemini support | `agents/config.py`                                                                       | 1-2 hours (investigation) |
| 7   | Fresh database + KB load               | Database, seed scripts                                                                   | 2-3 hours                 |

### P1 — Should Do (demo quality)

| #   | Task                                     | Files                                          | Effort  |
| --- | ---------------------------------------- | ---------------------------------------------- | ------- |
| 8   | Update seed script for Thai demo company | `seed_demo_data.py`                            | 2 hours |
| 9   | Fix AITE branding remnants               | 4 files                                        | 30 min  |
| 10  | Update metadata descriptions             | `layout.tsx`, `pyproject.toml`, `pubspec.yaml` | 30 min  |
| 11  | Update email domain                      | `settings.py`, 3 adapter files                 | 30 min  |
| 12  | Set LLM budget for demo company to $50+  | Admin panel or DB                              | 5 min   |
| 13  | Pre-test 5 scripted advisory questions   | Manual testing                                 | 1 hour  |

### P2 — Nice to Have (polish)

| #   | Task                                      | Files                       | Effort    |
| --- | ----------------------------------------- | --------------------------- | --------- |
| 14  | Build minimal Thai KB (10-20 provisions)  | New KB content module       | 4-6 hours |
| 15  | Update frontend Singapore references      | 12+ files                   | 2-3 hours |
| 16  | Update mobile app Singapore references    | 9 files                     | 2-3 hours |
| 17  | Add `jurisdiction` field to Company model | `company_user.py` + routing | 1-2 weeks |

### P3 — Post-Demo (if engagement proceeds)

| #   | Task                                                              | Effort    |
| --- | ----------------------------------------------------------------- | --------- |
| 18  | Full Thai calculator suite (SSF, PIT, severance, leave, overtime) | 2-3 weeks |
| 19  | Thai specialist agents (6 domains)                                | 1-2 weeks |
| 20  | Thai guardrail patterns                                           | 1 week    |
| 21  | Thai statutory filing formats                                     | 1-2 weeks |
| 22  | Bilingual advisory (Thai + English)                               | 1-2 weeks |
| 23  | Jurisdiction-aware platform architecture                          | 2-4 weeks |

---

## Decision Required: LiteLLM vs Direct Gemini SDK

**Option A — LiteLLM abstraction** (recommended):

- Add `litellm` dependency
- Change model strings from `gpt-4o` to `gemini/gemini-2.0-flash`
- LiteLLM auto-translates function calling format
- Future provider switches become trivial
- Effort: 1-2 days

**Option B — Direct Gemini SDK**:

- Add `google-generativeai` dependency
- Rewrite all 5 files with Gemini-native API calls
- Must manually transpile function calling schema (214 lines of tool definitions)
- Tighter integration but locked to Gemini
- Effort: 3-5 days

**Option C — Keep OpenAI SDK, point at Gemini-compatible endpoint**:

- Google offers OpenAI-compatible API endpoint for Gemini
- Minimal code changes (just endpoint URL + model name)
- May not support all features (function calling compatibility varies)
- Effort: 1 day (but risky)

---

## Risk Register

| Risk                                                | Likelihood | Impact | Mitigation                                                                      |
| --------------------------------------------------- | ---------- | ------ | ------------------------------------------------------------------------------- |
| Gemini function calling incompatibility             | Medium     | High   | Test the 7 calculator tool definitions thoroughly. Have OpenAI key as fallback. |
| Gemini embedding quality differs                    | Low        | Medium | Test KB retrieval quality with Gemini embeddings. May need prompt tuning.       |
| Kaizen framework doesn't support Gemini             | Medium     | High   | Check Kaizen docs. May need LiteLLM as bridge.                                  |
| Demo hits $5 budget cap                             | High       | High   | Set demo company budget to $50+ before demo                                     |
| MULTI_JURISDICTION guardrail rejects Thai questions | High       | High   | Only ask SG questions live. Frame Thai as "what this would look like."          |
| Server restart clears in-memory conversations       | Medium     | Medium | Prep demo right before. Or accept fresh conversations.                          |
| Gemini latency differs from OpenAI                  | Medium     | Low    | Pre-warm with one query. Time responses during testing.                         |
