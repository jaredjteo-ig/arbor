# T001: Project Scaffolding and Repository Structure

**Milestone**: M1 — Foundation
**Status**: PENDING
**Priority**: CRITICAL — blocks every other task in the project
**Estimated Effort**: 4-6 hours

---

## Description

Set up the monorepo structure for the HR AI Advisory platform. The repository already exists as a Kailash COC workspace at the project root. This task adapts the generic scaffolding to the specific requirements of the HR advisory product: updating project metadata, creating the backend Python package, scaffolding both frontends, configuring local development infrastructure, and verifying the test runner works end-to-end.

All Kailash framework dependencies are already listed in `pyproject.toml` (`kailash`, `kailash-nexus`, `kailash-dataflow`, `kailash-kaizen`). The root `conftest.py` already auto-loads `.env`. This task fills the gaps and resolves the placeholder values.

---

## Acceptance Criteria

- [ ] `pyproject.toml` has the correct project name, description, and author metadata (no TODO placeholders remain)
- [ ] `src/` directory exists with a proper Python package structure for the HR advisory backend
- [ ] `apps/web/` exists as a scaffolded React/Next.js project with TypeScript, TanStack Query, and React Hook Form
- [ ] `apps/mobile/` exists as a scaffolded Flutter project with Riverpod, GoRouter, and Dio
- [ ] `docker-compose.dev.yml` starts cleanly with `docker compose up` (PostgreSQL + pgvector + Redis, no errors)
- [ ] `.env.example` covers all required variables (LLM keys, database URLs, Redis URL, JWT secret, Google OAuth, app settings)
- [ ] `pytest` runs from the project root and collects tests without import errors
- [ ] `conftest.py` loads `.env` correctly (confirmed by existing implementation — no changes required)

---

## Dependencies

- None — this is the root task; no other task can start until T001 is complete

---

## Risk Assessment

- **HIGH**: `apps/web/` and `apps/mobile/` scaffold commands (`create-next-app`, `flutter create`) require the respective toolchains to be installed. Verify Node.js/npm and Flutter SDK are available before starting subtask 3 and 4.
- **MEDIUM**: `pyproject.toml` `setuptools.packages.find` is currently configured to scan from `.` (project root). After creating `src/`, the `where` value should be updated to `["src"]` or the package structure confirmed to work with the current setting.
- **LOW**: pgvector is a PostgreSQL extension that requires a specific Docker image (`pgvector/pgvector:pg16` or `ankane/pgvector`). Using the plain `postgres` image will cause T007 to fail silently at runtime.

---

## Subtasks

### S1: Update pyproject.toml with correct project metadata

**Estimated time**: 30 minutes

**What to do**:

Open `/Users/esperie/repos/asme/aite/pyproject.toml` and replace all placeholder values:

```
name = "my-kailash-project"          → "hr-ai-advisory"
description = "A Kailash SDK project" → "AI-powered HR compliance advisory platform for Singapore SMEs"
authors name/email                   → actual author details
```

Uncomment the `[project.urls]` section and add appropriate URLs once the repository is hosted.

Update `[tool.setuptools.packages.find]` to point at `src/` once that directory is created:

```toml
[tool.setuptools.packages.find]
where = ["src"]
exclude = ["tests*", ".*", "__pycache__*"]
```

**Verification**: `python -m build --no-isolation` completes without errors (or `pip install -e .` succeeds).

---

### S2: Create src/ directory structure for the backend Python package

**Estimated time**: 45 minutes

**What to do**:

Create the following directory and file structure under `/Users/esperie/repos/asme/aite/src/`:

```
src/
  hr_advisory/                    # main Python package
    __init__.py
    config.py                     # settings loaded from env (never hardcoded values)
    models/
      __init__.py
      # DataFlow model definitions will go here (T007, T008)
    agents/
      __init__.py
      # Kaizen agent definitions will go here (T010, T010A, T010B)
    workflows/
      __init__.py
      # Core SDK workflow definitions will go here (T011, T020-T022)
    api/
      __init__.py
      # Nexus endpoint registrations will go here (T009)
    services/
      __init__.py
      # Business logic bridging agents/workflows to API
```

`config.py` should load all settings from `os.environ` (populated via `.env`). Do not hardcode any values. Example pattern:

```python
import os

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
# LLM model names from env — never hardcoded
DEFAULT_LLM_MODEL = os.environ.get("DEFAULT_LLM_MODEL", "")
```

Create a minimal smoke-test to confirm the package is importable:
`tests/unit/test_package_import.py`:

```python
def test_package_imports():
    import hr_advisory
    import hr_advisory.config
```

**Verification**: `pytest tests/unit/test_package_import.py` passes.

---

### S3: Create apps/web/ React project scaffolding

**Estimated time**: 60 minutes

**Prerequisite**: Node.js 18+ and npm/pnpm installed.

**What to do**:

From the project root, scaffold a Next.js project with TypeScript:

```bash
cd /Users/esperie/repos/asme/aite
npx create-next-app@latest apps/web \
  --typescript \
  --tailwind \
  --eslint \
  --app \
  --src-dir \
  --import-alias "@/*"
```

After scaffolding, install required dependencies:

```bash
cd apps/web
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install react-hook-form @hookform/resolvers zod
npm install react-router-dom   # if not using Next.js routing
npm install axios              # for API client (T013)
npm install i18next react-i18next  # for i18n (T002)
```

Create the initial directory structure inside `apps/web/src/`:

```
src/
  app/                      # Next.js App Router pages
  components/
    design-system/          # T003 components go here
  services/
    api/                    # T013 API service layer goes here
  hooks/                    # TanStack Query hooks
  providers/                # React context providers
  lib/                      # Utilities
  locales/
    en/                     # i18n translation files
      common.json
      advisory.json
```

**Verification**: `npm run dev` starts without errors and the browser shows the default Next.js page at `http://localhost:3000`.

---

### S4: Create apps/mobile/ Flutter project scaffolding

**Estimated time**: 60 minutes

**Prerequisite**: Flutter SDK installed and `flutter doctor` shows no critical errors.

**What to do**:

From the project root:

```bash
cd /Users/esperie/repos/asme/aite
flutter create apps/mobile \
  --project-name hr_advisory_mobile \
  --org com.hraidvisory \
  --platforms android,ios
```

After scaffolding, add required dependencies to `apps/mobile/pubspec.yaml`:

```yaml
dependencies:
  flutter:
    sdk: flutter
  flutter_riverpod: ^2.5.0
  riverpod_annotation: ^2.3.0
  go_router: ^13.0.0
  dio: ^5.4.0
  flutter_secure_storage: ^9.0.0
  hive_flutter: ^1.1.0
  intl: ^0.19.0 # for i18n/date formatting

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.0
  riverpod_generator: ^2.4.0
  json_serializable: ^6.7.0
```

Create the initial directory structure inside `apps/mobile/lib/`:

```
lib/
  main.dart
  app.dart                  # GoRouter setup
  core/
    design/
      tokens.dart           # Design tokens (T002)
      components/           # T004 components go here
    network/
      api_client.dart       # Dio client (T013)
    localization/
      l10n.dart
      arb/
        app_en.arb          # English strings
  features/
    auth/                   # T012
    advisory/               # T027
    calculators/            # T031
    documents/              # T033
    compliance/             # T035
    profile/                # T039
    alerts/                 # T038
```

**Verification**: `flutter run` (with a connected device or emulator) launches without compile errors and shows the default Flutter counter screen.

---

### S5: Create docker-compose.dev.yml for local development

**Estimated time**: 45 minutes

**What to do**:

Create `/Users/esperie/repos/asme/aite/docker-compose.dev.yml`:

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: hr_advisory_postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-hradvisory}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-hradvisory_dev}
      POSTGRES_DB: ${POSTGRES_DB:-hr_advisory}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-hradvisory}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: hr_advisory_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

Create `/Users/esperie/repos/asme/aite/docker/postgres/init.sql`:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify extension is available
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

Confirm the DATABASE_URL and REDIS_URL in `.env.example` match the docker-compose defaults:

- `DATABASE_URL=postgresql://hradvisory:hradvisory_dev@localhost:5432/hr_advisory`
- `REDIS_URL=redis://localhost:6379/0`

**Verification**:

```bash
docker compose -f docker-compose.dev.yml up -d
docker compose -f docker-compose.dev.yml ps   # both services show "healthy"
docker exec hr_advisory_postgres psql -U hradvisory -d hr_advisory -c "SELECT extname FROM pg_extension WHERE extname='vector';"
# should return: vector
```

---

### S6: Update .env.example with all required environment variables

**Estimated time**: 30 minutes

**What to do**:

Expand `/Users/esperie/repos/asme/aite/.env.example` to cover all variables the HR advisory platform requires. The current file covers LLM keys, database URL, JWT, and basic app settings. Add the following sections:

```bash
# ── Database (matches docker-compose.dev.yml defaults) ──────
DATABASE_URL=postgresql://hradvisory:hradvisory_dev@localhost:5432/hr_advisory
REDIS_URL=redis://localhost:6379/0

# Docker-compose vars (used by docker-compose.dev.yml)
# POSTGRES_USER=hradvisory
# POSTGRES_PASSWORD=hradvisory_dev
# POSTGRES_DB=hr_advisory

# ── Authentication ───────────────────────────────────────────
# JWT_SECRET_KEY=change-this-to-a-random-string-at-least-32-chars
# JWT_EXPIRY_HOURS=24
# JWT_REFRESH_EXPIRY_DAYS=30

# ── Google OAuth2 (for T012 Google sign-in) ─────────────────
# GOOGLE_OAUTH_CLIENT_ID=your-client-id.apps.googleusercontent.com
# GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret

# ── Email (for T038 notifications and T012 password reset) ──
# SENDGRID_API_KEY=SG.your-key-here
# EMAIL_FROM_ADDRESS=noreply@hraidvisory.com
# EMAIL_FROM_NAME=HR AI Advisory

# ── File Storage (for T034 document generation) ─────────────
# STORAGE_BACKEND=local          # local | s3 | gcs
# LOCAL_STORAGE_PATH=./storage/documents
# AWS_S3_BUCKET=hr-advisory-documents   # if STORAGE_BACKEND=s3
# AWS_REGION=ap-southeast-1

# ── Push Notifications (for T056 Flutter push) ──────────────
# FCM_SERVER_KEY=your-fcm-server-key

# ── Application ─────────────────────────────────────────────
# APP_ENV=development            # development | staging | production
# DEBUG=true
# LOG_LEVEL=INFO
# ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8080
```

**Verification**: All variables referenced in `src/hr_advisory/config.py` (S2) have a corresponding entry in `.env.example`. No variable appears in code that is absent from the template.

---

### S7: Verify conftest.py works with the new structure

**Estimated time**: 20 minutes

**What to do**:

The existing `conftest.py` at `/Users/esperie/repos/asme/aite/conftest.py` is already correct — it loads `.env` from `Path(__file__).parent / ".env"`, which resolves to the project root. No code changes are needed.

Verify it works with the new `src/` package:

1. Copy `.env.example` to `.env` and fill in the minimum required values (at least one LLM key and the local database URL)
2. Run `pytest --collect-only` from the project root — confirm it collects tests without `ModuleNotFoundError`
3. Run the package import smoke test from S2: `pytest tests/unit/test_package_import.py -v`
4. Confirm that `os.environ["DATABASE_URL"]` is populated inside a test (add a quick assertion to the smoke test)

If `pytest --collect-only` fails with import errors, the `src/` directory needs to be on the Python path. Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

**Verification**: `pytest tests/unit/test_package_import.py -v` shows 1 passed, 0 errors.

---

## Testing Requirements

- **Unit**: Package import test (S2/S7) — confirms Python package structure is correct
- **Infrastructure**: `docker compose up` health checks (S5) — confirms PostgreSQL + pgvector + Redis are reachable
- **Manual smoke**: `npm run dev` (S3) and `flutter run` (S4) — confirms frontend scaffolds build and run
- **No integration or E2E tests** at this stage — those require T007 (data models) and T009 (API layer)

---

## Definition of Done

- [ ] All 7 subtasks completed
- [ ] No TODO placeholders remain in `pyproject.toml`
- [ ] `pytest` runs cleanly from project root (0 errors, 0 import failures)
- [ ] `docker compose -f docker-compose.dev.yml up -d` brings up healthy PostgreSQL+pgvector+Redis
- [ ] `apps/web/` runs with `npm run dev`
- [ ] `apps/mobile/` compiles with `flutter build apk --debug` (or `flutter run`)
- [ ] `.env.example` documents every variable used anywhere in the codebase
- [ ] T002 (design tokens) and T007 (DataFlow models) are unblocked and can begin
