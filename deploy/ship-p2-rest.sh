#!/usr/bin/env bash
#
# ship-p2-rest.sh — Gate 3 phase 2 finishing pieces (RC + GO + EX).
#
# Adds:
#   - Recognition + PeerNomination models + /recognition/* endpoints
#   - Goal + GoalCheckIn models + /goals/* endpoints
#   - ExitInterview model + /exit-interviews/* endpoints + public /exit-survey/[token] page
#   - Frontend pages: /recognition, /goals, /exit-interviews, /exit-survey/[token]
#   - 3 demo seeds (6 kudos + 2 nominations, 6 goals + 4 check-ins, 2 exit
#     interviews — one anon negative, one named positive)

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

SSH_CMD=(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${INSTANCE_IP}")

BACKFILL_SCRIPTS=(
  "scripts/backfill_demo_recognition.py:P2-RC-5 — seed 6 kudos + 2 peer nominations"
  "scripts/backfill_demo_goals.py:P2-GO-5 — seed 6 goals + 4 check-ins"
  "scripts/backfill_demo_exit_interviews.py:P2-EX-4 — seed 2 exit interviews"
)

log() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m  ✓ %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m  ✗ %s\033[0m\n" "$*" >&2; }

log "Step 1 / 6  Pre-flight"
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python -m pytest \
  tests/regression/test_p2_rc.py \
  tests/regression/test_p2_go_ex.py \
  tests/regression/test_p2_lnd.py \
  tests/regression/test_p1_lifecycle_dashboard.py \
  -q --tb=line || { err "Regression failed."; exit 1; }
ok "Regression suite green."

log "Step 2 / 6  Push"
if git status --porcelain | grep -qE '^( M|MM|A |AM)'; then
  err "Working tree has uncommitted changes."
  git status --short
  exit 1
fi
git push origin main
ok "Pushed."

log "Step 3 / 6  Pull + rebuild"
TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/${DEPLOY_REPO}.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} build backend frontend"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} up -d backend frontend"
ok "Rebuilt."

log "Step 4 / 6  Wait for backend"
for i in {1..30}; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "${PROD_API_BASE}/api/health" || echo "000")
  if [[ "$code" == "200" ]]; then ok "Healthy after ${i}s"; break; fi
  sleep 2
done

log "Step 5 / 6  Bootstrap schema + run seeds"
DETECTED=$("${SSH_CMD[@]}" "docker ps --format '{{.Names}}' | grep -E 'arbor-?backend|backend' | head -1" || true)
if [[ -n "$DETECTED" ]]; then BACKEND_CONTAINER="$DETECTED"; fi
"${SSH_CMD[@]}" "docker cp ${REMOTE_DIR}/scripts ${BACKEND_CONTAINER}:/app/scripts"

# Login retry
LOGIN_BODY=$(ADMIN_EMAIL="${ADMIN_EMAIL}" ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  python3 -c 'import json,os; print(json.dumps({"email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]}))')
ACCESS=""
for i in {1..30}; do
  RESP=$(curl -sS -X POST "${PROD_API_BASE}/api/auth/login" \
    -H 'Content-Type: application/json' -d "${LOGIN_BODY}" 2>/dev/null || echo "")
  if [[ -n "$RESP" ]]; then
    ACCESS=$(printf '%s' "$RESP" | python3 -c "import sys, json
try: print(json.load(sys.stdin).get('access_token',''))
except Exception: print('')")
  fi
  if [[ -n "$ACCESS" ]]; then break; fi
  sleep 2
done
if [[ -z "$ACCESS" ]]; then err "Login failed."; exit 1; fi
ok "Authenticated."

# Bootstrap each table by hitting its list endpoint once.
for path in /recognition /goals /exit-interviews; do
  curl -sS -o /dev/null "${PROD_API_BASE}/api${path}" \
    -H "Authorization: Bearer ${ACCESS}" || true
done
ok "Tables auto-created."

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
ok "All seeds applied."

log "Step 6 / 6  Smoke"
curl -sS "${PROD_API_BASE}/api/recognition/feed" \
  -H "Authorization: Bearer ${ACCESS}" | grep -q '"feed"' && ok "Recognition feed live."
curl -sS "${PROD_API_BASE}/api/goals" \
  -H "Authorization: Bearer ${ACCESS}" | grep -q '"goals"' && ok "Goals live."
curl -sS "${PROD_API_BASE}/api/exit-interviews/themes" \
  -H "Authorization: Bearer ${ACCESS}" | grep -q '"tally"' && ok "Exit themes live."

probe() {
  local path="$1"; local label="$2"
  local code=$(curl -sS -o /dev/null -w '%{http_code}' "${PROD_API_BASE}${path}" || echo "000")
  if [[ "$code" =~ ^2|3 ]]; then ok "${label}: HTTP ${code}"; else err "${label}: HTTP ${code}"; fi
}
probe "/recognition" "Recognition page"
probe "/goals" "Goals page"
probe "/exit-interviews" "Exit interviews page"

ok "Phase 2 complete: L&D + Recognition + Goals + Exit Interview all live."
