#!/usr/bin/env bash
# Clone the live production database to your local Docker Postgres so local
# matches what's running at 136.110.51.61.
#
# What it does:
#   1. pg_dump live (compressed custom format) over SSH
#   2. terminate any open backend connections to the local DB
#   3. DROP + CREATE the local arbor database
#   4. pg_restore the dump
#
# Prerequisites:
#   - Local Docker stack up (`docker compose -f docker-compose.dev.yml up -d`)
#   - SSH key at ~/.ssh/google_compute_engine works for jaredteo@136.110.51.61
#
# WARNING: this WIPES your local arbor database. Any local-only test data is lost.

set -euo pipefail

LIVE_HOST="${LIVE_HOST:-136.110.51.61}"
LIVE_USER="${LIVE_USER:-jaredteo}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/google_compute_engine}"
LIVE_CONTAINER="${LIVE_CONTAINER:-arbor-postgres}"
LOCAL_CONTAINER="${LOCAL_CONTAINER:-arbor-postgres}"
DB_USER="${DB_USER:-arbor}"
DB_NAME="${DB_NAME:-arbor}"
DUMP_PATH="${DUMP_PATH:-/tmp/arbor-live.dump}"

cyan()  { printf "\033[36m%s\033[0m\n" "$*"; }
green() { printf "\033[32m%s\033[0m\n" "$*"; }
red()   { printf "\033[31m%s\033[0m\n" "$*" >&2; }

if ! docker ps --format '{{.Names}}' | grep -qx "$LOCAL_CONTAINER"; then
  red "Local Postgres container '$LOCAL_CONTAINER' is not running."
  red "Start it first:  docker compose -f docker-compose.dev.yml up -d"
  exit 1
fi

cyan "1/4  Dumping live DB from ${LIVE_USER}@${LIVE_HOST}..."
ssh -i "$SSH_KEY" "${LIVE_USER}@${LIVE_HOST}" \
    "docker exec ${LIVE_CONTAINER} pg_dump -U ${DB_USER} -Fc ${DB_NAME}" \
    > "$DUMP_PATH"
size=$(ls -lh "$DUMP_PATH" | awk '{print $5}')
green "     wrote ${DUMP_PATH} (${size})"

cyan "2/4  Terminating open connections to local '${DB_NAME}'..."
docker exec -i "$LOCAL_CONTAINER" psql -U "$DB_USER" -d postgres -c \
    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${DB_NAME}' AND pid <> pg_backend_pid();" \
    > /dev/null

cyan "3/4  Dropping and recreating local '${DB_NAME}'..."
docker exec -i "$LOCAL_CONTAINER" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};" > /dev/null
docker exec -i "$LOCAL_CONTAINER" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};" > /dev/null

cyan "4/4  Restoring dump..."
docker exec -i "$LOCAL_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --no-acl < "$DUMP_PATH"

green ""
green "Done. Local now mirrors live."
docker exec "$LOCAL_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
    "SELECT 'users' AS table, COUNT(*) FROM users
     UNION ALL SELECT 'companies', COUNT(*) FROM companies
     UNION ALL SELECT 'job_listings', COUNT(*) FROM job_listings
     UNION ALL SELECT 'candidates', COUNT(*) FROM candidates
     UNION ALL SELECT 'kb_provisions', COUNT(*) FROM provisions
     UNION ALL SELECT 'kb_acts', COUNT(*) FROM acts;"

green ""
green "Restart the backend to reconnect with the new schema:"
echo  "    pkill -f 'hr_advisory.api.server' && \\"
echo  "    source .venv/bin/activate && python -m hr_advisory.api.server &"
