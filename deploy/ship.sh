#!/usr/bin/env bash
# ship.sh — Deploy to production via git pull + docker rebuild
#
# Usage: ./deploy/ship.sh [--backend-only] [--frontend-only]
#
# Workflow:
#   1. Push local commits to GitHub
#   2. SSH to server, git pull
#   3. Rebuild and restart Docker containers
#   4. Verify health

set -euo pipefail

SERVER="ec2-user@52.220.50.167"
SSH_KEY="${HOME}/.ssh/ai-coach.pem"
REMOTE_DIR="/opt/aite"
SSH="ssh -i ${SSH_KEY} ${SERVER}"

BUILD_BACKEND=true
BUILD_FRONTEND=true

if [[ "${1:-}" == "--backend-only" ]]; then
  BUILD_FRONTEND=false
elif [[ "${1:-}" == "--frontend-only" ]]; then
  BUILD_BACKEND=false
fi

echo "=== Step 1: Push to GitHub ==="
git push origin main

echo ""
echo "=== Step 2: Pull on server ==="
TOKEN=$(gh auth token)
${SSH} "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/esperie/aite.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"

echo ""
echo "=== Step 3: Rebuild containers ==="
SERVICES=""
if $BUILD_BACKEND; then SERVICES="${SERVICES} backend"; fi
if $BUILD_FRONTEND; then SERVICES="${SERVICES} frontend"; fi

${SSH} "cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build ${SERVICES}"

echo ""
echo "=== Step 4: Verify health ==="
sleep 20
${SSH} "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '---' && curl -sf https://aite.kailash.ai/api/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"status\",\"?\"))'"

echo ""
echo "=== Deployed ==="
