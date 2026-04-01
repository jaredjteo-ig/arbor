#!/usr/bin/env bash
# ship.sh — Deploy Central to AWS EC2 (central.kailash.ai)
#
# Usage: ./deploy/ship.sh [--backend-only] [--frontend-only]
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - SSH key for EC2 instance (~/.ssh/central-prod.pem or ssh-agent)
#   - EC2 instance running with Docker + Docker Compose installed
#
# Workflow:
#   1. Push local commits to GitHub
#   2. SSH to EC2 instance, git pull
#   3. Rebuild and restart Docker containers
#   4. Verify health

set -euo pipefail

# ── Configuration ──────────────────────────────────────────
INSTANCE_IP="${CENTRAL_INSTANCE_IP:-}"  # Set in .env or export before running
SSH_KEY="${CENTRAL_SSH_KEY:-~/.ssh/central-prod.pem}"
SSH_USER="${CENTRAL_SSH_USER:-ubuntu}"
REMOTE_DIR="/opt/arbor"
DOMAIN="central.kailash.ai"

if [[ -z "$INSTANCE_IP" ]]; then
  echo "ERROR: Set CENTRAL_INSTANCE_IP before running."
  echo "  export CENTRAL_INSTANCE_IP=<your-ec2-public-ip>"
  exit 1
fi

SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no ${SSH_USER}@${INSTANCE_IP}"

BUILD_BACKEND=true
BUILD_FRONTEND=true

if [[ "${1:-}" == "--backend-only" ]]; then
  BUILD_FRONTEND=false
elif [[ "${1:-}" == "--frontend-only" ]]; then
  BUILD_BACKEND=false
fi

echo "=== Step 1: Push to GitHub ==="
git push origin main 2>/dev/null || git push terrene main 2>/dev/null || echo "Push skipped (no remote or already up to date)"

echo ""
echo "=== Step 2: Pull on server ==="
TOKEN=$(gh auth token 2>/dev/null || echo "")
if [[ -n "$TOKEN" ]]; then
  ${SSH_CMD} "cd ${REMOTE_DIR} && git remote set-url origin https://x-access-token:${TOKEN}@github.com/terrene-foundation/arbor.git && git fetch origin main && git reset --hard origin/main && git log --oneline -1"
else
  ${SSH_CMD} "cd ${REMOTE_DIR} && git pull origin main && git log --oneline -1"
fi

echo ""
echo "=== Step 3: Rebuild containers ==="
SERVICES=""
if $BUILD_BACKEND; then SERVICES="${SERVICES} backend"; fi
if $BUILD_FRONTEND; then SERVICES="${SERVICES} frontend"; fi

${SSH_CMD} "cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build ${SERVICES}"

echo ""
echo "=== Step 4: Verify health ==="
sleep 20
${SSH_CMD} "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '---' && curl -sf https://${DOMAIN}/api/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"status\",\"?\"))'"

echo ""
echo "=== Deployed to https://${DOMAIN} ==="
