# Seed Script Rules

## Scope

These rules apply to any data-seeding script in this repo (e.g., `scripts/seed_demo_data.py`, `scripts/seed_employees.py`, `scripts/seed_kb.py`) and to any future seeding utility that runs against a deployed environment.

## Why these rules exist

On 2026-04-29 a monolithic seed script crashed mid-run on prod (httpx connection-reset from DataFlow pool saturation), and the round-13 sections at the end never executed. A bypass runner failed at login because the script's hardcoded password did not match the prod admin's password. Both failures stem from the same anti-patterns:

- A single `main()` that runs everything in one chain — one section's failure kills all later sections
- Hardcoded credentials with no env-var override
- No retry/backoff on transient HTTP errors
- No way to run a subset of sections (e.g., "just refresh the round-13 demo data")
- Hardcoded `company_id=1` defaults that break on multi-tenant prod databases

## MUST Rules

### 1. Modular sections + section registry

Every seed script with more than 3 logical phases MUST expose a `--section` flag and a section registry. Each section MUST be:

- Named (kebab-case, stable across releases)
- Self-contained (one logical unit of seeding)
- Idempotent (safe to re-run without duplicating rows)
- Wrapped in try/except by the runner so its failure does not kill subsequent sections

The runner MUST emit a final summary line listing OK/FAIL counts and the failure detail for each failed section. Exit code MUST be non-zero if any section fails (for CI catch).

```python
# Example pattern
parser.add_argument("--section", action="append", help="Section name or alias")
parser.add_argument("--list-sections", action="store_true")
parser.add_argument("--dry-run", action="store_true")

CANONICAL_SECTIONS = [
    ("auth", _section_auth, "Register/login admin"),
    ("company", _section_company, "Create/find company"),
    # ...
]
SECTION_ALIASES = {
    "all": [name for name, _, _ in CANONICAL_SECTIONS],
    "demo-refresh": ["auth", "lookup-company", "candidate-pdpa", ...],
}
```

### 2. Env-var credentials

Admin credentials MUST be readable from environment variables. Hardcoded fallbacks are acceptable for local dev only and MUST be flagged in code comments.

```python
# DO:
DEFAULT_EMAIL = os.environ.get("ADMIN_EMAIL", "demo@local.dev")
DEFAULT_PASSWORD = os.environ.get("ADMIN_PASSWORD", "LocalDev123!")

# DO NOT:
DEFAULT_EMAIL = "demo@local.dev"
DEFAULT_PASSWORD = "LocalDev123!"  # No way to override on prod
```

### 3. Production safety guard

Seed scripts that mutate data MUST refuse to run against any non-localhost API URL when using a default password (i.e., when `ADMIN_PASSWORD` env var is unset). This prevents accidental destructive runs against prod.

```python
def _validate_prod_password(api_url: str, password: str) -> None:
    is_local = "localhost" in api_url or "127.0.0.1" in api_url
    if is_local:
        return
    if password == DEFAULT_LOCAL_PASSWORD and not os.environ.get("ADMIN_PASSWORD"):
        sys.exit(2)  # Refuse to proceed
```

### 4. Retry + backoff on transient failures

Every HTTP call from a seed script MUST go through a retry helper that handles:

- `httpx.ReadError`, `httpx.WriteError`, `httpx.ConnectError`, `httpx.RemoteProtocolError`
- `httpx.PoolTimeout`, `httpx.ReadTimeout`
- HTTP 429, 502, 503, 504

Backoff MUST be exponential with jitter, max 5 attempts by default, capped at 30s per sleep.

DataFlow pool saturation (pool_size=70 + max_overflow=35 vs Postgres max_connections=100) is the typical cause of ECONNRESET — retry handles it without operator intervention.

### 5. Dry-run + list-sections

Every seed script MUST support:

- `--list-sections` — print available sections + aliases, exit
- `--dry-run` — print the section plan WITHOUT executing, exit 0

Operators run dry-run before any prod invocation to verify the plan.

### 6. No hardcoded company_id

Sections that take a `company_id` parameter MUST NOT default it to `1` or any other literal. If a section needs a company_id, it MUST be passed in by the caller (typically resolved by an upstream `lookup-company` section). Hardcoded `=1` defaults break on multi-tenant prod databases where company 1 may not exist or may belong to someone else.

```python
# DO:
def seed_scorecard_templates(client, company_id: int) -> None: ...

# DO NOT:
def seed_scorecard_templates(client, company_id: int = 1) -> None: ...
```

### 7. Lookup before create for refresh sections

"Refresh" sections (operating on existing data) MUST resolve the target company by lookup, not by creation. Provide a `lookup-company` bootstrap section that calls `/auth/me` (or equivalent) to resolve `company_id` from the authenticated admin's session — never recreate the company.

### 8. Direct-SQL only when API can't express the field

Direct DB writes (psycopg2) bypass model validation, audit logging, and transactional guarantees provided by the API. They are acceptable ONLY when:

- No API endpoint exists for the field being written (e.g., template-level preboarding tasks before TODO-XX added the endpoint)
- The seed flow runs after many earlier API calls have exhausted the backend's connection pool, AND retry/backoff still fails

When using direct SQL, MUST:

- Use parameterized queries (`%s` placeholders) — never string concatenation
- Wrap in `with conn:` / `with conn.cursor() as cur:` for automatic transaction commit
- Document WHY direct SQL was chosen (link to the missing API)
- Track creation of the missing API as a follow-up

### 9. Probability-weighted demo distributions (P52)

Demo seed data with categorical buckets (e.g. every IC tagged
"growth"+"manager") reads as fake the moment a buyer sees the
identical bin sizes. Demo distributions MUST be probability-weighted
with at least three bands plus background variance.

**Why this rule exists:** the engagement-survey post-walk polish
caught a seed that tagged 100% of low-scoring engineering ICs with
both "growth" and "manager" themes. Manager view showed
`growth ×7, manager ×7` for a 7-report team — buyers immediately
read it as seed data, not signal.

**Pattern:**

```python
# Three probability bands per category — focal / adjacent / background
if is_resigner:
    growth_prob = 0.90        # focal
elif dept.startswith("eng") and target_avg < 3.5:
    growth_prob = 0.70        # focal-adjacent
elif dept.startswith("eng"):
    growth_prob = 0.25        # adjacent
else:
    growth_prob = 0.08        # background
if rng.random() < growth_prob:
    themes_for_response.append("growth")

# Plus a background draw across other categories for variance
theme_roll = rng.random()
if theme_roll < 0.15:
    themes_for_response.append("workload")
elif theme_roll < 0.25:
    themes_for_response.append("recognition")
# ... etc, total background coverage 30-45%
```

**Calibration heuristic:** focal 70-90%, adjacent 15-30%,
background 5-10% per item. Hit rates of 100% / 0% read as fake;
hit rates of 30% / 30% / 30% read as real.

**Determinism:** seed `random.Random(seed_int)` so reproducible
runs produce identical distributions. Don't use unseeded `rng` —
demos that drift between resets confuse buyers.

### 10. Wipe-before-reseed when distribution logic changes

Idempotent seeds with a "skip if already seeded" guard (e.g.
`if existing >= 6: return`) are correct for first-run safety but
prevent re-runs from picking up updated logic. When the seed
_logic_ changes (probability bands, theme catalogue, calibration),
the existing rows still reflect old logic.

**Pattern:** document a wipe SQL block alongside the seed script,
parameterised by `company_id`. Do NOT bake "wipe-on-rerun" into the
script itself — that's destructive on prod by accident.

```sql
-- Run before re-seeding when distribution logic changes:
DELETE FROM engagement_actions WHERE company_id=:cid;
DELETE FROM engagement_survey_responses WHERE company_id=:cid;
DELETE FROM engagement_surveys WHERE company_id=:cid;
```

The wipe must hit _child_ rows before _parent_ rows (FK ordering)
and must be `company_id`-scoped (never company-wide). After wipe,
re-run the seed inside the backend container (the script is not
baked into the image — copy it in via `docker cp`).

## MUST NOT Rules

### 1. No single monolithic main() that chains all sections

A monolithic `main()` where each step depends on the prior step's success and one failure halts the rest is a known anti-pattern. The runner MUST iterate through sections and isolate failures.

### 2. No silent skips on missing dependencies

If a section requires state from an earlier section (e.g., `salary-components` needs the employees list), the runner MUST raise a clear error naming the missing dependency, not silently skip or use stale data.

### 3. No password in CLI args without env-var fallback

Any `--password` CLI flag MUST default to an env var (`ADMIN_PASSWORD`), not a hardcoded string. Passwords on the command line leak to shell history; env vars do not.

## Cross-references

- `.claude/rules/security.md` — global no-hardcoded-secrets policy
- `.claude/rules/env-models.md` — env-var-as-source-of-truth for keys/models
- `scripts/seed_demo_data.py` — canonical implementation of all 8 rules
