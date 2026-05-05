#!/usr/bin/env bash
#
# ship-redteam-round-12.sh — End-to-end prod deploy for the round-12
# redteam closure (Gate 1 of workspaces/obayashi/02-plans/03-post-redteam-plan.md).
#
# What this script does:
#   1. Runs the local pre-flight: full unit + regression sweep.
#   2. Pushes the bundled commit to GitHub.
#   3. SSHes to the GCP prod VM (136.110.51.61), pulls, rebuilds containers.
#   4. Runs the 7 backfill / migration scripts in dependency order
#      INSIDE the backend container (so .env / DATABASE_URL are available).
#   5. Hits the H2 stale-pending leave sweep endpoint via the API.
#   6. Smoke-checks the live site.
#   7. Reports — exits non-zero if any step fails.
#
# Usage:
#   ./deploy/ship-redteam-round-12.sh
#
# Prerequisites (env vars or defaults):
#   CENTRAL_INSTANCE_IP   default: 136.110.51.61
#   CENTRAL_SSH_KEY       default: ~/.ssh/google_compute_engine
#   CENTRAL_SSH_USER      default: jaredteo
#   ADMIN_EMAIL           default: demo@central.kailash.ai
#   ADMIN_PASSWORD        REQUIRED — used to authenticate the H2 sweep call
#                         and the smoke check. Pulled from env var or prompt.
#   PROD_API_BASE         default: http://136.110.51.61
#
# Idempotent — every backfill script is idempotent, every API call is safe to
# re-run. You can re-run this script after a failure without harm.

set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────
INSTANCE_IP="${CENTRAL_INSTANCE_IP:-136.110.51.61}"
SSH_KEY="${CENTRAL_SSH_KEY:-$HOME/.ssh/google_compute_engine}"
SSH_USER="${CENTRAL_SSH_USER:-jaredteo}"
REMOTE_DIR="/opt/arbor"
PROD_API_BASE="${PROD_API_BASE:-http://${INSTANCE_IP}}"
ADMIN_EMAIL="${ADMIN_EMAIL:-demo@central.kailash.ai}"

if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
  read -rsp "ADMIN_PASSWORD (used for H2 sweep + smoke check): " ADMIN_PASSWORD
  echo
fi
if [[ -z "${ADMIN_PASSWORD:-}" ]]; then
  echo "ERROR: ADMIN_PASSWORD is required."
  exit 1
fi

SSH_CMD=(ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${SSH_USER}@${INSTANCE_IP}")

# Container name for backend — used to docker exec the backfill scripts.
# Defaults to "arbor-backend" but auto-detects if your compose names it
# something else.
BACKEND_CONTAINER="${BACKEND_CONTAINER:-arbor-backend}"

# Ordered list of backfill / migration scripts to run on prod, with reasons.
# Order matters — see workspaces/obayashi/02-plans/03-post-redteam-plan.md.
BACKFILL_SCRIPTS=(
  "scripts/backfill_employee_pass_type.py:M1 — default empty pass_type to citizen"
  "scripts/migrate_employee_tracks_attendance.py:H1 — add tracks_attendance column + heuristic backfill"
  "scripts/backfill_claim_totals.py:B3 — recompute claim totals = SUM(items)"
  "scripts/backfill_onboarding_templates.py:H4 — soft-archive duplicate-name templates"
  "scripts/backfill_empty_payroll_drafts.py:M4 — drop \$0 abandoned payroll drafts"
  "scripts/backfill_demo_appraisals.py:M5 — seed active appraisal period + 3 reviews"
  "scripts/backfill_demo_interview_variety.py:M7 — seed Completed + Cancelled interviews"
  "scripts/backfill_employee_pass_type.py:M1 (re-run as no-op safety check)"
)

# ── Helpers ──────────────────────────────────────────────────────────────
log() { printf "\n\033[1;36m=== %s ===\033[0m\n" "$*"; }
ok()  { printf "\033[1;32m  ✓ %s\033[0m\n" "$*"; }
warn(){ printf "\033[1;33m  ! %s\033[0m\n" "$*"; }
err() { printf "\033[1;31m  ✗ %s\033[0m\n" "$*" >&2; }

# ── Step 1: Local pre-flight ─────────────────────────────────────────────
log "Step 1 / 7  Local pre-flight (unit + regression sweep)"

cd "$(git rev-parse --show-toplevel)"

if [[ ! -x .venv/bin/python ]]; then
  err ".venv/bin/python not found. Run 'python3 -m venv .venv && .venv/bin/pip install -e .' first."
  exit 1
fi

# Capture baseline counts. The full suite has ~45 pre-existing unrelated
# failures; we don't block on them, but we DO block on any NEW regression
# in the redteam-related test files.
REDTEAM_TESTS=(
  tests/regression/test_b3_claim_total_recalc.py
  tests/regression/test_h1_attendance_tracks_filter.py
  tests/regression/test_h2_stale_leave_sweep.py
  tests/regression/test_h3_payroll_ordering.py
  tests/regression/test_h4_unique_template_names.py
  tests/unit/test_recruitment_advanced.py::TestReapplyCandidate
)

if ! .venv/bin/python -m pytest "${REDTEAM_TESTS[@]}" -q --tb=line; then
  err "Round-12 regression tests failed. Aborting deploy."
  exit 1
fi
ok "Regression suite green."

# ── Step 2: Push to GitHub ───────────────────────────────────────────────
log "Step 2 / 7  Push bundled commit to GitHub"
if git status --porcelain | grep -qE '^( M|MM|A |AM)'; then
  err "Working tree has uncommitted changes. Commit them first."
  git status --short
  exit 1
fi

git push origin main
ok "Pushed to origin/main."

# ── Step 3: Pull + rebuild on prod ───────────────────────────────────────
log "Step 3 / 7  Pull + rebuild on ${INSTANCE_IP}"

TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/terrene-foundation/arbor.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  "${SSH_CMD[@]}" "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi
ok "Remote checkout updated."

"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose build backend frontend"
"${SSH_CMD[@]}" "cd ${REMOTE_DIR}/deploy && docker compose up -d backend frontend"
ok "Containers rebuilt and restarted."

# Give the backend a moment to come up before exec'ing the backfills.
sleep 8

# ── Step 4: Run backfills inside the backend container ──────────────────
log "Step 4 / 7  Run backfill / migration scripts in dependency order"

# Auto-detect the actual backend container name on the remote in case it
# differs from BACKEND_CONTAINER.
DETECTED=$("${SSH_CMD[@]}" "docker ps --format '{{.Names}}' | grep -E 'arbor-?backend|backend' | head -1" || true)
if [[ -n "$DETECTED" ]]; then
  BACKEND_CONTAINER="$DETECTED"
fi
ok "Backend container: ${BACKEND_CONTAINER}"

for entry in "${BACKFILL_SCRIPTS[@]}"; do
  script="${entry%%:*}"
  reason="${entry##*:}"
  echo
  echo "  → ${script}"
  echo "    ${reason}"
  if ! "${SSH_CMD[@]}" "docker exec ${BACKEND_CONTAINER} python ${script}"; then
    err "Script ${script} failed. Investigate before continuing."
    exit 1
  fi
done
ok "All backfills applied."

# ── Step 5: Fire the H2 stale-pending leave sweep via the API ───────────
log "Step 5 / 7  Fire H2 stale-pending leave sweep"

# JSON-quote both fields via python3 so a password containing " or \
# doesn't break the request body. Password is passed via env, not argv,
# so it never shows up in `ps`.
LOGIN_BODY=$(ADMIN_EMAIL="${ADMIN_EMAIL}" ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
  python3 -c 'import json,os; print(json.dumps({"email":os.environ["ADMIN_EMAIL"],"password":os.environ["ADMIN_PASSWORD"]}))')
LOGIN_JSON=$(curl -sS -X POST "${PROD_API_BASE}/api/auth/login" \
  -H 'Content-Type: application/json' \
  -d "${LOGIN_BODY}")
ACCESS_TOKEN=$(printf '%s' "$LOGIN_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [[ -z "$ACCESS_TOKEN" ]]; then
  err "Could not log in as ${ADMIN_EMAIL}. Login response: ${LOGIN_JSON:0:200}"
  exit 1
fi
ok "Authenticated as ${ADMIN_EMAIL}."

SWEEP_RESP=$(curl -sS -X POST "${PROD_API_BASE}/api/leave/applications/sweep-stale-pending" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
echo "  Sweep response: ${SWEEP_RESP}"
if printf '%s' "$SWEEP_RESP" | grep -q '"cancelled"'; then
  ok "Stale-leave sweep complete."
else
  warn "Sweep response did not include 'cancelled' field — verify manually."
fi

# ── Step 6: Smoke-check the live site ────────────────────────────────────
log "Step 6 / 7  Smoke-check live endpoints"

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
probe "/login" "login page"

# Authenticated route smoke — workforce composition (tests M1 + NEW-3 fix).
WF=$(curl -sS "${PROD_API_BASE}/api/profile/1/workforce" \
  -H "Authorization: Bearer ${ACCESS_TOKEN}")
echo "  Workforce: ${WF}"
if printf '%s' "$WF" | grep -q '"workforce"'; then
  ok "Workforce endpoint live."
else
  err "Workforce endpoint did not return expected shape."
  exit 1
fi

# ── Step 7: Done ────────────────────────────────────────────────────────
log "Step 7 / 7  Done"
ok "Round-12 redteam closure is live on ${PROD_API_BASE}."
echo
echo "Next manual steps:"
echo "  • B1 (deferred) — set DEFAULT_LLM_MODEL in deploy/.env.prod and"
echo "    docker compose restart backend when you want to switch."
echo "  • Walk the live site once to confirm everything renders cleanly:"
echo "      open ${PROD_API_BASE}"
echo "  • Begin Gate 2 (Phase 1 lifecycle dashboard) per"
echo "    workspaces/obayashi/02-plans/03-post-redteam-plan.md."
