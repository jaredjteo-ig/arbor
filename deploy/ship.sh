#!/usr/bin/env bash
# ship.sh — Deploy Arbor to GCP (arbor.terrene.foundation)
#
# Usage: ./deploy/ship.sh [--backend-only] [--frontend-only]
#
# Workflow:
#   1. Push local commits to GitHub
#   2. SSH to GCE VM, git pull
#   3. Rebuild and restart Docker containers
#   4. Verify health

set -euo pipefail

PROJECT="terrene-care"
ZONE="asia-southeast1-b"
INSTANCE="arbor-prod"
REMOTE_DIR="/opt/arbor"
DOMAIN="arbor.terrene.foundation"
SSH="gcloud compute ssh ${INSTANCE} --project=${PROJECT} --zone=${ZONE} --command"

BUILD_BACKEND=true
BUILD_FRONTEND=true

if [[ "${1:-}" == "--backend-only" ]]; then
  BUILD_FRONTEND=false
elif [[ "${1:-}" == "--frontend-only" ]]; then
  BUILD_BACKEND=false
fi

echo "=== Step 1: Push to GitHub ==="
git push terrene main

echo ""
echo "=== Step 2: Pull on server ==="
TOKEN=$(gh auth token)
${SSH} "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/terrene-foundation/arbor.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"

echo ""
echo "=== Step 3: Rebuild containers ==="
SERVICES=""
if $BUILD_BACKEND; then SERVICES="${SERVICES} backend"; fi
if $BUILD_FRONTEND; then SERVICES="${SERVICES} frontend"; fi

${SSH} "cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build ${SERVICES}"

echo ""
echo "=== Step 4: Verify health ==="
sleep 20
${SSH} "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '---' && curl -sf https://${DOMAIN}/api/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"status\",\"?\"))'"

echo ""
echo "=== Deployed to https://${DOMAIN} ==="
