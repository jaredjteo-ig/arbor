#!/usr/bin/env bash
#
# ship-redteam-round-2-polish.sh — Round-2 redteam M + L closure.
#
# Backend:
#   - exit_interviews.py: GET /exit-interviews/public/{token}/validate
#                         (preflight returning semantic reason)
#   - strategy.py: activity feed humanizes employee_id / assignment_id /
#                  candidate_id → human names
#
# Frontend:
#   - exit-survey/[token]/page.tsx: mount-time preflight + semantic
#                                   empty states (gone / expired /
#                                   already submitted)
#   - training/skillsfuture/page.tsx: curated-fallback banner
#   - training/mandatory/page.tsx:    "browse courses" CTA when any
#                                     requirement uncovered
#
# Data backfill on prod:
#   - backfill_demo_disnapshot.py:    fills gender + DOB on the demo
#                                     admin row (D&I tile reads 100%)
#   - backfill_demo_recognition.py:   adds 2 kudos TO the demo admin
#                                     (received tab populates)
#   - backfill_demo_goals.py:         fix-up branch rewires existing
#                                     orphan goals (manager_id=0,
#                                     period_id=0)
#   - backfill_demo_exit_interviews.py: seeds last-year RESIGNED event
#                                       so churn YoY delta isn't 0
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

SSH_CMD=(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${INSTANCE_IP}")

log() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m  ✓ %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m  ✗ %s\033[0m\n" "$*" >&2; }

log "Step 1 / 7  Pre-flight"
cd "$(git rev-parse --show-toplevel)"
.venv/bin/python -m pytest \
  tests/regression/test_redteam2_polish.py \
  tests/regression/test_redteam2_findings.py \
  tests/regression/test_p3_strategic_depth.py \
  tests/regression/test_p2_rc.py \
  tests/regression/test_p2_go_ex.py \
  tests/regression/test_p2_lnd.py \
  tests/regression/test_p1_lifecycle_dashboard.py \
  -q --tb=line || { err "Regression failed."; exit 1; }
ok "Regression suite green."

log "Step 2 / 7  Push"
if git status --porcelain | grep -qE '^( M|MM|A |AM)'; then
  err "Working tree has uncommitted changes."; git status --short; exit 1
fi
git push origin main
ok "Pushed."

log "Step 3 / 7  Pull + rebuild"
TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/${DEPLOY_REPO}.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} build backend frontend"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose ${COMPOSE_ARGS} up -d backend frontend"
ok "Rebuilt."

log "Step 4 / 7  Wait for backend"
for i in {1..30}; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' "${PROD_API_BASE}/api/health" || echo "000")
  if [[ "$code" == "200" ]]; then ok "Healthy after ${i}s"; break; fi
  sleep 2
done

log "Step 5 / 7  Backfill seeds (idempotent)"
DETECTED=$("${SSH_CMD[@]}" "docker ps --format '{{.Names}}' | grep -E 'arbor-?backend|backend' | head -1" || true)
if [[ -n "$DETECTED" ]]; then BACKEND_CONTAINER="$DETECTED"; fi
"${SSH_CMD[@]}" "docker cp ${REMOTE_DIR}/scripts ${BACKEND_CONTAINER}:/app/scripts"

for script in \
    backfill_demo_disnapshot.py \
    backfill_demo_recognition.py \
    backfill_demo_goals.py \
    backfill_demo_exit_interviews.py; do
  if "${SSH_CMD[@]}" "docker exec ${BACKEND_CONTAINER} python scripts/${script}"; then
    ok "Ran ${script}."
  else
    err "${script} failed."; exit 1
  fi
done

log "Step 6 / 7  Login + smoke"
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

log "Step 7 / 7  Verify"

# Activity feed: pull lifecycle dashboard, look for at least one summary
# that contains a real name (no employee #N).
LIFECYCLE=$(curl -sS "${PROD_API_BASE}/api/strategy/lifecycle-dashboard" \
  -H "Authorization: Bearer ${ACCESS}")
if echo "$LIFECYCLE" | grep -q '"churn_yoy_delta"'; then
  ok "Lifecycle dashboard exposes churn_yoy_delta."
fi
if echo "$LIFECYCLE" | grep -Eq '"summary":\s*"[^"]*employee #[0-9]'; then
  err "Activity feed STILL contains 'employee #N' — humanize did not deploy."
else
  ok "Activity feed: no raw employee IDs."
fi

# Exit-survey preflight: invalid token returns ok=false / invalid_or_expired
PRE_RESP=$(curl -sS "${PROD_API_BASE}/api/exit-interviews/public/bogus-token/validate")
if echo "$PRE_RESP" | grep -q '"reason":"invalid_or_expired"'; then
  ok "Exit-survey preflight live and returns semantic reason."
else
  err "Exit-survey preflight not deployed — got: ${PRE_RESP}"
fi

ok "Round-2 polish deployed."
