# Local Development & Testing

This is the **fast iteration loop**. Use this for active development, testing
changes before pushing, and red-team / E2E test runs that need many cycles.

**Round-trip time:** ~5 seconds (hot reload). Compare with the GCP deploy at
~3-5 minutes per cycle (see `PRODUCTION.md`).

## What runs where

| Service                  | Mode   | Port   | How                                |
| ------------------------ | ------ | ------ | ---------------------------------- |
| Postgres (pgvector/pg16) | Docker | `5432` | `docker-compose.dev.yml`           |
| Redis (7-alpine)         | Docker | `6379` | `docker-compose.dev.yml`           |
| Backend (FastAPI/Nexus)  | Native | `8001` | `python -m hr_advisory.api.server` |
| Frontend (Next.js)       | Native | `3001` | `npm run dev` (in `apps/web/`)     |

Backend + frontend run NATIVELY (not in containers) so hot reload works:

- Backend: edit `src/hr_advisory/**/*.py` → uvicorn auto-reloads
- Frontend: edit `apps/web/src/**/*.tsx` → Next.js Fast Refresh reloads

## First-time setup

```bash
cd /Users/jaredteo/Documents/GitHub/arbor

# 1. Python venv (already exists; skip if present)
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 2. Frontend deps
cd apps/web && npm install && cd ../..

# 3. .env (copy template, fill in keys)
cp .env.example .env
# Edit .env: set DATABASE_URL=postgresql://arbor:arbor@localhost:5432/arbor
#            set REDIS_URL=redis://:@localhost:6379
#            set OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.
```

## Daily workflow

### Start everything

```bash
# Terminal 1 — services (Postgres + Redis only)
docker compose -f docker-compose.dev.yml up -d
docker ps --format "table {{.Names}}\t{{.Status}}"   # confirm both healthy

# Terminal 2 — backend
source .venv/bin/activate
python -m hr_advisory.api.server
# Backend at http://localhost:8001
# OpenAPI docs: http://localhost:8001/docs

# Terminal 3 — frontend
cd apps/web
npm run dev
# Frontend at http://localhost:3001
```

### Run migration on local DB (after schema changes)

```bash
.venv/bin/python scripts/migrate_recruitment_fields.py
# Idempotent — safe to re-run
```

### Seed local DB with demo data (fresh state)

```bash
# Drop and recreate everything (DESTRUCTIVE — local only)
docker compose -f docker-compose.dev.yml down -v   # removes volumes
docker compose -f docker-compose.dev.yml up -d

# Wait for postgres healthcheck, then seed
.venv/bin/python -c "
from hr_advisory.services.company_seeding import seed_company_defaults
# Run through your normal signup flow first, then call seeding manually
"
```

### Run tests

```bash
# All recruitment + cross-cutting unit tests (fast)
.venv/bin/python -m pytest tests/unit/test_recruitment_*.py \
    tests/unit/test_screening_questions.py \
    tests/unit/test_tafep_scanner.py \
    tests/unit/test_rate_limit.py \
    --timeout=30 -q --no-header > /tmp/tests.out 2>&1
tail -30 /tmp/tests.out

# CRITICAL: never pipe pytest through grep/tail when run as a background task
# — pipe buffering produces empty output. Always redirect to a file first.
```

### Stop everything

```bash
# Frontend / backend: Ctrl+C in their terminals
# Services:
docker compose -f docker-compose.dev.yml down

# To wipe local DB too:
docker compose -f docker-compose.dev.yml down -v
```

## When to use local vs GCP

| Scenario                               | Use                   |
| -------------------------------------- | --------------------- |
| Iterating on a feature                 | Local                 |
| Writing tests                          | Local                 |
| Red-team / E2E test runs (many cycles) | Local                 |
| Integration testing across services    | Local                 |
| Verifying a fix works end-to-end       | Local first, then GCP |
| Demo to a customer                     | GCP                   |
| Validating production deployment       | GCP                   |
| Smoke testing after a release          | GCP                   |

## Troubleshooting

- **Backend won't start, "DATABASE_URL not set"**: check `.env` exists and has
  the local Postgres URL. The root `conftest.py` auto-loads it for pytest.
- **Frontend can't reach backend**: confirm `NEXT_PUBLIC_API_URL=http://localhost:8001`
  in `apps/web/.env.local` (or root `.env`).
- **"Connection refused" to localhost:5432**: postgres container died or port
  collision. `docker ps` to check; `lsof -i :5432` to find conflicts.
- **Tests hang with empty output**: you piped pytest through `tail`/`grep` in a
  background task. ALWAYS redirect to a file (`> /tmp/x.out 2>&1`) instead.
- **`pytest-asyncio` not detected**: confirm `pyproject.toml` has it in `[dev]`
  and you ran `pip install -e ".[dev]"`.
