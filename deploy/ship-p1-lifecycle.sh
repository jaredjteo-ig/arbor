#!/usr/bin/env bash
#
# ship-p1-lifecycle.sh — End-to-end deploy for Gate 2 (Phase 1 lifecycle dashboard).
#
# Adds the new /strategy/lifecycle surface + employer-brand migration on
# top of the round-12 redteam closure already on prod. Runs the same
# local-preflight + push + remote pull + container rebuild flow as
# ship-redteam-round-12.sh, plus the new P1-7 column-add migration.
#
# Idempotent: safe to re-run if any step fails.
#
# Usage:
#   ./deploy/ship-p1-lifecycle.sh
# or
#   ADMIN_PASSWORD='...' ./deploy/ship-p1-lifecycle.sh

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────
INSTANCE_IP="${CENTRAL_INSTANCE_IP:-136.110.51.61}"
SSH_KEY="${CENTRAL_SSH_KEY:-$HOME/.ssh/google_compute_engine}"
SSH_USER="${CENTRAL_SSH_USER:-jaredteo}"
REMOTE_DIR="/opt/arbor"
PROD_API_BASE="${PROD_API_BASE:-http://${INSTANCE_IP}}"
ADMIN_EMAIL="${ADMIN_EMAIL:-demo@central.kailash.ai}"
DEPLOY_REPO="${GITHUB_DEPLOY_REPO:-jaredjteo-ig/arbor}"
COMPOSE_ARGS="-f docker-compose.prod.yml --env-file .env.prod"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-arbor-backend}"

if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
  read -rsp "ADMIN_PASSWORD: " ADMIN_PASSWORD
  echo
fi
if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
  echo "ERROR: ADMIN_PASSWORD is required."
  exit 1
fi

SSH_CMD=(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${INSTANCE_IP}")

# Migrations to run (only the new P1-7 column add — every other table
# already exists from earlier waves).
MIGRATION_SCRIPTS=(
  "scripts/migrate_company_employer_brand.py:P1-7 — Company employer-brand fields"
)

log() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m  ✓ %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m  ✗ %s\033[0m\n" "$*" >&2; }

# ── Step 1: Local pre-flight ─────────────────────────────────────────────
log "Step 1 / 6  Local pre-flight (P1 regression sweep)"
cd "$(git rev-parse --show-toplevel)"

if [[ ! -x .venv/bin/python ]]; then
  err ".venv/bin/python not found."
  exit 1
fi

if ! .venv/bin/python -m pytest \
  tests/regression/test_p1_lifecycle_dashboard.py \
  tests/regression/test_b3_claim_total_recalc.py \
  tests/regression/test_h1_attendance_tracks_filter.py \
  tests/regression/test_h2_stale_leave_sweep.py \
  tests/regression/test_h3_payroll_ordering.py \
  tests/regression/test_h4_unique_template_names.py \
  -q --tb=line; then
  err "Regression suite failed."
  exit 1
fi
ok "Regression suite green."

# ── Step 2: Push ─────────────────────────────────────────────────────────
log "Step 2 / 6  Push to GitHub"
if git status --porcelain | grep -qE '^( M|MM|A |AM)'; then
  err "Working tree has uncommitted changes."
  git status --short
  exit 1
fi
git push origin main
ok "Pushed to origin/main."

# ── Step 3: Pull + rebuild ───────────────────────────────────────────────
log "Step 3 / 6  Pull + rebuild on ${INSTANCE_IP}"
TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/${DEPLOY_REPO}.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} build backend frontend"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} up -d backend frontend"
ok "Containers rebuilt and restarted."
sleep 8

# ── Step 4: Run migrations ───────────────────────────────────────────────
log "Step 4 / 6  Run migrations"
DETECTED=$("${SSH_CMD[@]}" "docker ps --format '{{.Names}}' | grep -E 'arbor-?backend|backend' | head -1" || true)
if [[ -n "$DETECTED" ]]; then
  BACKEND_CONTAINER="$DETECTED"
fi
"${SSH_CMD[@]}" "docker cp ${REMOTE_DIR}/scripts ${BACKEND_CONTAINER}:/app/scripts"
ok "Scripts copied into ${BACKEND_CONTAINER}."

for entry in "${MIGRATION_SCRIPTS[@]}"; do
  script="${entry%%:*}"
  reason="${entry##*:}"
  echo
  echo "  → ${script}"
  echo "    ${reason}"
  if ! "${SSH_CMD[@]}" "docker exec ${BACKEND_CONTAINER} python ${script}"; then
    err "Migration ${script} failed."
    exit 1
  fi
done
ok "All migrations applied."

# ── Step 5: Smoke check ─────────────────────────────────────────────────
log "Step 5 / 6  Smoke-check live endpoints"
LOGIN_BODY=$(ADMIN_EMAIL="${ADMIN_EMAIL}" ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  python3 -c 'import json,os; print(json.dumps({"email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]}))')
LOGIN_JSON=$(curl -sS -X POST "${PROD_API_BASE}/api/auth/login" \
  -H 'Content-Type: application/json' -d "${LOGIN_BODY}")
ACCESS_TOKEN=$(printf '%s' "$LOGIN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")
if [[ -z "$ACCESS_TOKEN" ]]; then
  err "Login failed."
  exit 1
fi
ok "Authenticated."

LIFECYCLE=$(curl -sS "${PROD_API_BASE}/api/strategy/lifecycle-dashboard" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
if printf '%s' "$LIFECYCLE" | grep -q '"hero"' && printf '%s' "$LIFECYCLE" | grep -q '"stages"'; then
  ok "Lifecycle aggregator returning expected shape."
else
  err "Lifecycle aggregator did not return expected shape."
  echo "  Response: ${LIFECYCLE:0:300}"
  exit 1
fi

probe() {
  local path="$1"
  local label="$2"
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' "${PROD_API_BASE}${path}" || echo "000")
  if [[ "$code" =~ ^2|3 ]]; then
    ok "${label}: HTTP ${code}"
  else
    err "${label}: HTTP ${code}"
    return 1
  fi
}
probe "/" "frontend root"
probe "/api/health" "backend /api/health"
probe "/strategy/lifecycle" "lifecycle page"

# ── Step 6: Done ────────────────────────────────────────────────────────
log "Step 6 / 6  Done"
ok "Phase 1 (Lifecycle Dashboard) is live on ${PROD_API_BASE}."
echo
echo "Next: walk ${PROD_API_BASE}/strategy/lifecycle, then start Gate 3"
echo "      (P2-LD learning-development) per workspaces/obayashi/todos/active/."
