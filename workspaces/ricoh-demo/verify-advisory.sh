#!/usr/bin/env bash
# verify-advisory.sh — Run 5 scripted advisory questions against production
# Usage: API_URL=http://136.110.51.61:8001 ./workspaces/ricoh-demo/verify-advisory.sh
#
# Requires: curl, jq
# The script logs in, creates a conversation, sends 5 questions, and reports results.

set -euo pipefail

API_URL="${API_URL:-http://136.110.51.61:8001}"
EMAIL="${DEMO_EMAIL:-admin@central.sg}"
PASSWORD="${DEMO_PASSWORD:-admin123}"

echo "=== Advisory Verification Script ==="
echo "Target: ${API_URL}"
echo ""

# Step 1: Login
echo "--- Step 1: Login ---"
LOGIN_RESP=$(curl -sf -X POST "${API_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"${EMAIL}\", \"password\": \"${PASSWORD}\"}" 2>&1) || {
  echo "FAIL: Login failed. Check credentials and server status."
  echo "Response: ${LOGIN_RESP}"
  exit 1
}
TOKEN=$(echo "$LOGIN_RESP" | jq -r '.access_token // empty')
if [[ -z "$TOKEN" ]]; then
  echo "FAIL: No access_token in login response"
  echo "$LOGIN_RESP" | jq .
  exit 1
fi
echo "PASS: Logged in successfully"
echo ""

# Helper function to send advisory query and measure time
send_query() {
  local QUERY="$1"
  local EXPECTED_TIER="$2"
  local EXPECTED_DOMAIN="$3"
  local NUM="$4"

  echo "--- Question ${NUM}: ${QUERY:0:60}... ---"
  local START_TIME=$(date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1000))')

  local RESP=$(curl -sf -X POST "${API_URL}/advisory/query" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN}" \
    -d "{\"query\": \"${QUERY}\", \"company_id\": 1}" 2>&1) || {
    echo "  FAIL: Request failed"
    return 1
  }

  local END_TIME=$(date +%s%3N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1000))')
  local DURATION=$(( END_TIME - START_TIME ))

  # Extract key fields
  local RISK_TIER=$(echo "$RESP" | jq -r '.risk_tier // .risk_level // "unknown"')
  local HAS_CITATIONS=$(echo "$RESP" | jq -r 'if (.citations // .provisions_cited // []) | length > 0 then "yes" else "no" end')
  local RESPONSE_LEN=$(echo "$RESP" | jq -r '.response // .answer // "" | length')

  echo "  Latency: ${DURATION}ms"
  echo "  Risk tier: ${RISK_TIER} (expected: ${EXPECTED_TIER})"
  echo "  Has citations: ${HAS_CITATIONS}"
  echo "  Response length: ${RESPONSE_LEN} chars"

  # Validate
  local PASS=true
  if [[ "$RESPONSE_LEN" -lt 50 ]]; then
    echo "  WARN: Response suspiciously short"
    PASS=false
  fi
  if [[ "$DURATION" -gt 30000 ]]; then
    echo "  WARN: Latency >30s"
    PASS=false
  fi
  if $PASS; then
    echo "  RESULT: PASS"
  else
    echo "  RESULT: CHECK"
  fi
  echo ""
}

# Step 2: Run 5 scripted questions
echo "=== Running 5 Scripted Advisory Questions ==="
echo ""

send_query "What is the notice period for an employee who has worked for 3 years?" "AMBER" "employment_act" 1

send_query "What are the CPF contribution rates for a 35-year-old Singapore citizen earning \$5,000 per month?" "GREEN" "cpf" 2

send_query "What are an employer's obligations after a workplace injury occurs?" "AMBER" "wsh" 3

send_query "Can an employee be dismissed for refusing to work overtime? Is that wrongful dismissal?" "RED" "employment_act" 4

send_query "We are hiring a foreign worker for the first time. What do we need to know about quotas and levies?" "AMBER" "foreign_manpower" 5

echo "=== Verification Complete ==="
