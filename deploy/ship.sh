#!/usr/bin/env bash
# ship.sh — Deploy Arbor to GCP (arbor.terrene.foundation)
#
# Usage: ./deploy/ship.sh [version]
#
# Examples:
#   ./deploy/ship.sh              # deploys :latest
#   ./deploy/ship.sh 0.2.1        # deploys :0.2.1
#
# Workflow:
#   1. Copy compose + Caddyfile to server (if changed)
#   2. Pull Docker Hub images
#   3. Restart containers
#   4. Verify health

set -euo pipefail

PROJECT="terrene-care"
ZONE="asia-southeast1-b"
INSTANCE="arbor-prod"
REMOTE_DIR="/opt/arbor"
DOMAIN="arbor.terrene.foundation"
VERSION="${1:-latest}"
SSH="gcloud compute ssh ${INSTANCE} --project=${PROJECT} --zone=${ZONE} --command"

echo "=== Deploying Arbor v${VERSION} to ${DOMAIN} ==="

echo ""
echo "=== Step 1: Sync config files ==="
gcloud compute scp \
  deploy/docker-compose.prod.yml \
  deploy/Caddyfile \
  "${INSTANCE}:${REMOTE_DIR}/" \
  --project="${PROJECT}" --zone="${ZONE}"

echo ""
echo "=== Step 2: Pull images from Docker Hub ==="
${SSH} "cd ${REMOTE_DIR} && ARBOR_VERSION=${VERSION} docker compose -f docker-compose.prod.yml pull backend frontend"

echo ""
echo "=== Step 3: Restart containers ==="
${SSH} "cd ${REMOTE_DIR} && ARBOR_VERSION=${VERSION} docker compose -f docker-compose.prod.yml up -d"

echo ""
echo "=== Step 4: Verify health ==="
sleep 20
${SSH} "docker ps --format 'table {{.Names}}\t{{.Status}}' && echo '---' && curl -sf https://${DOMAIN}/api/health | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"status\",\"?\"))'"

echo ""
echo "=== Deployed v${VERSION} to https://${DOMAIN} ==="
