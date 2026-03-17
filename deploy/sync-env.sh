#!/usr/bin/env bash
# sync-env.sh — Sync environment variables from local .env to production .env.prod
#
# Usage: ./deploy/sync-env.sh [--dry-run]
#
# Syncs these keys from the project root .env to the server's deploy/.env.prod:
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_OAUTH_CLIENT_ID,
#   GOOGLE_OAUTH_CLIENT_SECRET, DEFAULT_LLM_MODEL
#
# Keys that are server-specific (DATABASE_URL, REDIS_*, JWT_SECRET_KEY, etc.)
# are NEVER synced — they stay as configured on the server.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL_ENV="${PROJECT_ROOT}/.env"
SERVER="ec2-user@52.220.50.167"
SSH_KEY="${HOME}/.ssh/ai-coach.pem"
REMOTE_ENV="/opt/aite/deploy/.env.prod"

# Keys to sync from local to server
SYNC_KEYS=(
  OPENAI_API_KEY
  ANTHROPIC_API_KEY
  DEFAULT_LLM_MODEL
  GOOGLE_OAUTH_CLIENT_ID
  GOOGLE_OAUTH_CLIENT_SECRET
)

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "[DRY RUN] Would sync these keys:"
fi

if [[ ! -f "$LOCAL_ENV" ]]; then
  echo "ERROR: No .env file found at $LOCAL_ENV"
  exit 1
fi

UPDATES=""
for key in "${SYNC_KEYS[@]}"; do
  local_val=$(grep "^${key}=" "$LOCAL_ENV" 2>/dev/null | head -1 | cut -d= -f2-)
  if [[ -z "$local_val" ]]; then
    continue
  fi

  if $DRY_RUN; then
    echo "  ${key}=${local_val:0:20}..."
  else
    # Build sed-safe replacement (remove the key line, append new one)
    UPDATES="${UPDATES}${key}=${local_val}\n"
  fi
done

if $DRY_RUN; then
  echo ""
  echo "Run without --dry-run to apply."
  exit 0
fi

if [[ -z "$UPDATES" ]]; then
  echo "No keys to sync."
  exit 0
fi

# Remove existing keys and append updated values
for key in "${SYNC_KEYS[@]}"; do
  local_val=$(grep "^${key}=" "$LOCAL_ENV" 2>/dev/null | head -1 | cut -d= -f2-)
  if [[ -n "$local_val" ]]; then
    ssh -i "$SSH_KEY" "$SERVER" "grep -v '^${key}=' ${REMOTE_ENV} > /tmp/env_sync.tmp && mv /tmp/env_sync.tmp ${REMOTE_ENV}"
    ssh -i "$SSH_KEY" "$SERVER" "echo '${key}=${local_val}' >> ${REMOTE_ENV}"
    echo "Synced: ${key} (${local_val:0:15}...)"
  fi
done

echo ""
echo "Keys synced. Restart the backend to apply:"
echo "  ssh -i $SSH_KEY $SERVER 'cd /opt/aite/deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d backend'"
