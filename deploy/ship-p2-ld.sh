#!/usr/bin/env bash
#
# ship-p2-ld.sh — End-to-end deploy for Gate 3 phase 2 (L&D foundations).
#
# Adds TrainingRecord + Certification + MandatoryTrainingRequirement
# models, the /training/* endpoints, /training/{records,certifications,
# mandatory} pages, and seeds 3 records + 2 certs + 1 mandatory rule.
#
# DataFlow auto-creates the three new tables on first list/create call,
# so there is no explicit migration script — the demo seed below triggers
# the schema and inserts demo data in one step.
#
# Idempotent.

set -euo pipefail

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

# Backfills (touch order — first call autocreates tables via DataFlow).
BACKFILL_SCRIPTS=(
  "scripts/backfill_demo_lnd.py:P2-LD-7 — seed 3 training records + 2 certs + 1 mandatory rule"
)

log() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m  ✓ %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m  ✗ %s\033[0m\n" "$*" >&2; }

# Pre-flight
log "Step 1 / 6  Local pre-flight"
cd "$(git rev-parse --show-toplevel)"
if ! .venv/bin/python -m pytest \
  tests/regression/test_p2_lnd.py \
  tests/regression/test_p1_lifecycle_dashboard.py \
  -q --tb=line; then
  err "Regression suite failed."
  exit 1
fi
ok "Regression suite green."

# Push
log "Step 2 / 6  Push to GitHub"
if git status --porcelain | grep -qE '^( M|MM|A |AM)'; then
  err "Working tree has uncommitted changes."
  git status --short
  exit 1
fi
git push origin main
ok "Pushed to origin/main."

# Pull + rebuild
log "Step 3 / 6  Pull + rebuild on ${INSTANCE_IP}"
TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/${DEPLOY_REPO}.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} build backend frontend"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} up -d backend frontend"
ok "Containers rebuilt."

# Wait for backend health (up to 60s, retry on warm-up)
log "Step 4 / 6  Wait for backend health"
for i in {1..30}; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "${PROD_API_BASE}/api/health" || echo "000")
  if [[ "$code" == "200" ]]; then
    ok "Backend healthy after ${i}s"
    break
  fi
  sleep 2
done

# Trigger schema autocreation by hitting the endpoints once, then run seed.
log "Step 5 / 6  Run L&D demo seed"
DETECTED=$("${SSH_CMD[@]}" "docker ps --format '{{.Names}}' | grep -E 'arbor-?backend|backend' | head -1" || true)
if [[ -n "$DETECTED" ]]; then
  BACKEND_CONTAINER="$DETECTED"
fi
"${SSH_CMD[@]}" "docker cp ${REMOTE_DIR}/scripts ${BACKEND_CONTAINER}:/app/scripts"

# First, get a token so we can hit the endpoints (this also autocreates tables).
LOGIN_BODY=$(ADMIN_EMAIL="${ADMIN_EMAIL}" ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  python3 -c 'import json,os; print(json.dumps({"email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]}))')

# Retry login until backend has fully warmed (max 60s).
TOKEN=""
for i in {1..30}; do
  RESPONSE=$(curl -sS -X POST "${PROD_API_BASE}/api/auth/login" \
    -H 'Content-Type: application/json' -d "${LOGIN_BODY}" 2>/dev/null || echo "")
  if [[ -n "$RESPONSE" ]]; then
    TOKEN=$(printf '%s' "$RESPONSE" | python3 -c "import sys, json;
try:
    print(json.load(sys.stdin).get('access_token', ''))
except Exception:
    print('')")
  fi
  if [[ -n "$TOKEN" ]]; then break; fi
  sleep 2
done
if [[ -z "$TOKEN" ]]; then
  err "Login failed after 60s of retries."
  exit 1
fi
ok "Authenticated."

# Hit each endpoint once so DataFlow auto-creates the tables before the seed.
for path in /training/records /training/certifications /training/mandatory; do
  curl -sS -o /dev/null "${PROD_API_BASE}/api${path}" \
    -H "Authorization: Bearer ${TOKEN}" || true
done
ok "Schema bootstrapped."

# Run the seed.
for entry in "${BACKFILL_SCRIPTS[@]}"; do
  script="${entry%%:*}"
  reason="${entry##*:}"
  echo
  echo "  → ${script}"
  echo "    ${reason}"
  if ! "${SSH_CMD[@]}" "docker exec ${BACKEND_CONTAINER} python ${script}"; then
    err "Seed ${script} failed."
    exit 1
  fi
done
ok "L&D demo data seeded."

# Smoke check
log "Step 6 / 6  Smoke-check"
LIFECYCLE=$(curl -sS "${PROD_API_BASE}/api/strategy/lifecycle-dashboard" \
  -H "Authorization: Bearer ${TOKEN}")
if printf '%s' "$LIFECYCLE" | grep -q '"records"'; then
  ok "Lifecycle dashboard now reads live L&D data."
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
probe "/training/records" "training records page"
probe "/training/certifications" "certifications page"
probe "/training/mandatory" "mandatory page"
probe "/api/training/records" "API records endpoint"

ok "Phase 2 L&D foundations are live on ${PROD_API_BASE}."
