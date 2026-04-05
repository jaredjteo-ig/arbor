#!/usr/bin/env bash
# ============================================================
# Arbor Build Toolkit — Configure Application Secrets
# ============================================================
#
# Creates the application namespace and all secrets needed to
# run Arbor. Auto-generates cryptographic secrets where possible.
# Only prompts for credentials you need to provide (Google, OpenAI).
#
# Your credentials are stored ONLY in your Kubernetes cluster.
#
# Usage:
#   ./configure.sh                    # Interactive setup
#   ./configure.sh --namespace myns   # Custom namespace (default: arbor)
#
# ============================================================
set -euo pipefail

# ── Configuration ──────────────────────────────────────────
APP_NAMESPACE="arbor"
SECRET_NAME="arbor-app-secrets"
DB_SECRET_NAME="arbor-db-credentials"

# ── Parse flags ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --namespace) APP_NAMESPACE="$2"; shift 2 ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

# ── Colors ─────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; BOLD=''; NC=''
fi

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()    { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
heading() { echo ""; echo -e "${BOLD}── $* ──${NC}"; }

# ── Crypto helpers ─────────────────────────────────────────
# Generate secrets without Python (pure shell + OpenSSL)
gen_password() {
    # 32 bytes, base64-encoded, URL-safe
    openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
}

gen_jwt_secret() {
    # 64 bytes for HS256
    openssl rand -base64 64 | tr -d '\n'
}

gen_fernet_key() {
    # Fernet key = 32 bytes, base64url-encoded with = padding
    openssl rand 32 | base64 | tr -d '\n'
}

# ── Input helpers ──────────────────────────────────────────
# Prompt with default value. Empty input = default.
prompt() {
    local varname="$1" message="$2" default="${3:-}"
    if [[ -n "${default}" ]]; then
        read -rp "${message} [${default}]: " value
        eval "${varname}=\"\${value:-${default}}\""
    else
        read -rp "${message}: " value
        eval "${varname}=\"\${value}\""
    fi
}

prompt_secret() {
    local varname="$1" message="$2"
    read -rsp "${message}: " value
    echo ""
    eval "${varname}=\"\${value}\""
}

prompt_optional() {
    local varname="$1" message="$2"
    read -rp "${message} (press Enter to skip): " value
    eval "${varname}=\"\${value}\""
}

prompt_secret_optional() {
    local varname="$1" message="$2"
    read -rsp "${message} (press Enter to skip): " value
    echo ""
    eval "${varname}=\"\${value}\""
}

# ── Validate ───────────────────────────────────────────────
validate_url() {
    local name="$1" value="$2"
    if [[ ! "${value}" =~ ^https://[a-zA-Z0-9._:/-]+$ ]]; then
        fail "${name} must be an HTTPS URL (got: ${value})"
    fi
}

# ── Preflight ──────────────────────────────────────────────
info "Checking prerequisites..."
command -v kubectl >/dev/null 2>&1 || fail "kubectl not found."
command -v openssl >/dev/null 2>&1 || fail "openssl not found."
kubectl cluster-info >/dev/null 2>&1 || fail "Cannot reach Kubernetes cluster."
ok "Connected to cluster"

# ── Intro ──────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  Arbor Application Configuration"
echo "============================================================"
echo ""
echo "  This will create all the secrets Arbor needs to run."
echo "  Passwords and keys are auto-generated where possible."
echo "  You only need to enter credentials you already have."
echo ""
echo "  Everything is stored in your cluster as Kubernetes Secrets."
echo "  Nothing is sent anywhere else."
echo ""
echo "============================================================"

# ── 1. Domain ──────────────────────────────────────────────
heading "Domain"

prompt ARBOR_DOMAIN "Your Arbor domain (e.g., arbor.example.com)" ""
if [[ -z "${ARBOR_DOMAIN}" ]]; then
    fail "Domain is required."
fi
if [[ "${ARBOR_DOMAIN}" =~ ^https?:// ]]; then
    fail "Enter the domain only, not the full URL (e.g., arbor.example.com)"
fi

FRONTEND_URL="https://${ARBOR_DOMAIN}"
API_URL="https://${ARBOR_DOMAIN}/api"
CORS_ORIGINS="https://${ARBOR_DOMAIN}"

ok "Domain: ${ARBOR_DOMAIN}"
ok "Frontend: ${FRONTEND_URL}"
ok "API: ${API_URL}"

# ── Detect existing secrets ────────────────────────────────
# If secrets already exist (re-run after data exists), offer to
# keep existing crypto material so running services aren't broken.
EXISTING_APP_SECRET=""
EXISTING_DB_SECRET=""
if kubectl get secret "${DB_SECRET_NAME}" -n "${APP_NAMESPACE}" >/dev/null 2>&1; then
    EXISTING_DB_SECRET="found"
fi
if kubectl get secret "${SECRET_NAME}" -n "${APP_NAMESPACE}" >/dev/null 2>&1; then
    EXISTING_APP_SECRET="found"
fi

read_existing_secret() {
    local secret_name="$1" key="$2"
    kubectl get secret "${secret_name}" -n "${APP_NAMESPACE}" \
        -o jsonpath="{.data.${key}}" 2>/dev/null | base64 -d 2>/dev/null || true
}

if [[ -n "${EXISTING_DB_SECRET}" || -n "${EXISTING_APP_SECRET}" ]]; then
    echo ""
    warn "Existing secrets found in namespace '${APP_NAMESPACE}'."
    warn "Re-generating passwords will break running databases/services!"
    echo ""
    read -rp "Keep existing passwords and keys? [Y/n]: " KEEP_EXISTING
    KEEP_EXISTING="${KEEP_EXISTING:-Y}"
fi

# ── 2. Database ────────────────────────────────────────────
heading "Database (PostgreSQL)"

DB_USER="arbor"
DB_NAME="arbor"

if [[ -n "${EXISTING_DB_SECRET}" && "${KEEP_EXISTING:-Y}" =~ ^[Yy] ]]; then
    DB_PASSWORD="$(read_existing_secret "${DB_SECRET_NAME}" POSTGRES_PASSWORD)"
    if [[ -n "${DB_PASSWORD}" ]]; then
        ok "Database password: keeping existing"
    else
        warn "Could not read existing password — generating new one"
        DB_PASSWORD="$(gen_password)"
    fi
else
    info "Auto-generating database credentials..."
    DB_PASSWORD="$(gen_password)"
fi
DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@arbor-postgres:5432/${DB_NAME}"

ok "Database user: ${DB_USER}"
ok "Database name: ${DB_NAME}"

# ── 3. Redis ───────────────────────────────────────────────
heading "Redis"

if [[ -n "${EXISTING_APP_SECRET}" && "${KEEP_EXISTING:-Y}" =~ ^[Yy] ]]; then
    REDIS_PASSWORD="$(read_existing_secret "${SECRET_NAME}" REDIS_PASSWORD)"
    if [[ -n "${REDIS_PASSWORD}" ]]; then
        ok "Redis password: keeping existing"
    else
        warn "Could not read existing password — generating new one"
        REDIS_PASSWORD="$(gen_password)"
    fi
else
    info "Auto-generating Redis password..."
    REDIS_PASSWORD="$(gen_password)"
fi
REDIS_URL="redis://:${REDIS_PASSWORD}@arbor-redis:6379/0"

# ── 4. Authentication ──────────────────────────────────────
heading "Authentication (JWT)"

JWT_ALGORITHM="HS256"
JWT_EXPIRY_MINUTES="60"

if [[ -n "${EXISTING_APP_SECRET}" && "${KEEP_EXISTING:-Y}" =~ ^[Yy] ]]; then
    JWT_SECRET="$(read_existing_secret "${SECRET_NAME}" JWT_SECRET_KEY)"
    if [[ -n "${JWT_SECRET}" ]]; then
        ok "JWT secret: keeping existing"
    else
        warn "Could not read existing JWT secret — generating new one"
        JWT_SECRET="$(gen_jwt_secret)"
    fi
else
    info "Auto-generating JWT signing secret..."
    JWT_SECRET="$(gen_jwt_secret)"
fi

ok "JWT algorithm: ${JWT_ALGORITHM}"

# ── 5. Encryption ──────────────────────────────────────────
heading "Encryption Keys"

if [[ -n "${EXISTING_APP_SECRET}" && "${KEEP_EXISTING:-Y}" =~ ^[Yy] ]]; then
    SALARY_ENCRYPTION_KEY="$(read_existing_secret "${SECRET_NAME}" SALARY_ENCRYPTION_KEY)"
    LLM_KEY_ENCRYPTION_KEY="$(read_existing_secret "${SECRET_NAME}" LLM_KEY_ENCRYPTION_KEY)"
    if [[ -n "${SALARY_ENCRYPTION_KEY}" && -n "${LLM_KEY_ENCRYPTION_KEY}" ]]; then
        ok "Encryption keys: keeping existing"
    else
        warn "Could not read existing keys — generating new ones"
        SALARY_ENCRYPTION_KEY="$(gen_fernet_key)"
        LLM_KEY_ENCRYPTION_KEY="$(gen_fernet_key)"
    fi
else
    info "Auto-generating Fernet encryption keys..."
    SALARY_ENCRYPTION_KEY="$(gen_fernet_key)"
    LLM_KEY_ENCRYPTION_KEY="$(gen_fernet_key)"
fi

# ── 6. Google OAuth (optional) ─────────────────────────────
heading "Google Sign-In (optional)"

echo ""
echo "  If you want users to sign in with their Google account,"
echo "  enter your Google OAuth credentials below."
echo "  Skip to disable Google Sign-In."
echo ""

prompt_optional GOOGLE_CLIENT_ID "Google OAuth Client ID"
GOOGLE_CLIENT_SECRET=""
GOOGLE_REDIRECT_URI=""

if [[ -n "${GOOGLE_CLIENT_ID}" ]]; then
    prompt_secret GOOGLE_CLIENT_SECRET "Google OAuth Client Secret (hidden)"
    GOOGLE_REDIRECT_URI="https://${ARBOR_DOMAIN}/auth/callback"
    ok "Google Sign-In: enabled"
    ok "Redirect URI: ${GOOGLE_REDIRECT_URI}"
    echo ""
    warn "Make sure this redirect URI is added in your Google Cloud Console:"
    warn "  ${GOOGLE_REDIRECT_URI}"
else
    ok "Google Sign-In: disabled (skipped)"
fi

# ── 7. LLM / AI (optional) ────────────────────────────────
heading "AI Advisory (optional)"

echo ""
echo "  Arbor uses an LLM for HR advisory. Enter your OpenAI API key"
echo "  to enable it, or skip to let users bring their own keys."
echo ""

prompt_secret_optional OPENAI_API_KEY "OpenAI API key (hidden)"

OPENAI_PROD_MODEL="gpt-4o-mini"
DEFAULT_LLM_MODEL="gpt-4o-mini"

if [[ -n "${OPENAI_API_KEY}" ]]; then
    ok "AI Advisory: enabled with server-provided key"
    prompt OPENAI_PROD_MODEL "LLM model name" "gpt-4o-mini"
    DEFAULT_LLM_MODEL="${OPENAI_PROD_MODEL}"
else
    ok "AI Advisory: BYOK only (users provide their own keys)"
fi

prompt_secret_optional ANTHROPIC_API_KEY "Anthropic API key (hidden, optional)"

# ── 8. Email (optional) ───────────────────────────────────
heading "Email Notifications (optional)"

prompt_secret_optional SENDGRID_API_KEY "SendGrid API key (hidden)"
FROM_EMAIL="noreply@${ARBOR_DOMAIN}"

if [[ -n "${SENDGRID_API_KEY}" ]]; then
    prompt FROM_EMAIL "From email address" "noreply@${ARBOR_DOMAIN}"
    ok "Email: enabled via SendGrid"
else
    ok "Email: disabled (skipped)"
fi

# ── 9. TLS / HTTPS ───────────────────────────────────────
heading "TLS / HTTPS Certificates"

echo ""
echo "  If you have cert-manager installed in your cluster,"
echo "  Arbor can automatically obtain TLS certificates from"
echo "  Let's Encrypt. Skip if you handle TLS externally"
echo "  (e.g., load balancer, Cloudflare, or manual certs)."
echo ""

TLS_ENABLED="false"
CERT_ISSUER="letsencrypt-prod"

read -rp "Enable automatic TLS via cert-manager? [y/N]: " TLS_CHOICE
TLS_CHOICE="${TLS_CHOICE:-N}"

if [[ "${TLS_CHOICE}" =~ ^[Yy] ]]; then
    TLS_ENABLED="true"
    prompt CERT_ISSUER "ClusterIssuer name" "letsencrypt-prod"
    ok "TLS: enabled (issuer: ${CERT_ISSUER})"
else
    ok "TLS: disabled (handle externally or configure later)"
fi

# ── 10. Image version ─────────────────────────────────────
heading "Image Version"

prompt ARBOR_VERSION "Arbor image tag to deploy" "latest"
prompt REGISTRY_ORG "Docker Hub org/user" "terrenefoundation"

ok "Backend image: ${REGISTRY_ORG}/arbor-backend:${ARBOR_VERSION}"
ok "Frontend image: ${REGISTRY_ORG}/arbor-frontend:${ARBOR_VERSION}"

# ── Create namespace ───────────────────────────────────────
heading "Creating resources"

kubectl create namespace "${APP_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -
ok "Namespace: ${APP_NAMESPACE}"

# ── Create database secret (separate for postgres container) ──
kubectl create secret generic "${DB_SECRET_NAME}" \
    --namespace="${APP_NAMESPACE}" \
    --from-literal=POSTGRES_USER="${DB_USER}" \
    --from-literal=POSTGRES_PASSWORD="${DB_PASSWORD}" \
    --from-literal=POSTGRES_DB="${DB_NAME}" \
    --dry-run=client -o yaml | kubectl apply -f -

ok "Secret: ${DB_SECRET_NAME}"

# ── Create application secret ─────────────────────────────
kubectl create secret generic "${SECRET_NAME}" \
    --namespace="${APP_NAMESPACE}" \
    --from-literal=DATABASE_URL="${DATABASE_URL}" \
    --from-literal=REDIS_PASSWORD="${REDIS_PASSWORD}" \
    --from-literal=REDIS_URL="${REDIS_URL}" \
    --from-literal=JWT_SECRET_KEY="${JWT_SECRET}" \
    --from-literal=JWT_ALGORITHM="${JWT_ALGORITHM}" \
    --from-literal=JWT_EXPIRY_MINUTES="${JWT_EXPIRY_MINUTES}" \
    --from-literal=SALARY_ENCRYPTION_KEY="${SALARY_ENCRYPTION_KEY}" \
    --from-literal=LLM_KEY_ENCRYPTION_KEY="${LLM_KEY_ENCRYPTION_KEY}" \
    --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
    --from-literal=OPENAI_PROD_MODEL="${OPENAI_PROD_MODEL}" \
    --from-literal=DEFAULT_LLM_MODEL="${DEFAULT_LLM_MODEL}" \
    --from-literal=ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}" \
    --from-literal=GOOGLE_OAUTH_CLIENT_ID="${GOOGLE_CLIENT_ID:-}" \
    --from-literal=GOOGLE_OAUTH_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-}" \
    --from-literal=GOOGLE_OAUTH_REDIRECT_URI="${GOOGLE_REDIRECT_URI:-}" \
    --from-literal=SENDGRID_API_KEY="${SENDGRID_API_KEY:-}" \
    --from-literal=FROM_EMAIL="${FROM_EMAIL}" \
    --from-literal=CORS_ORIGINS="${CORS_ORIGINS}" \
    --from-literal=FRONTEND_URL="${FRONTEND_URL}" \
    --from-literal=APP_ENV="production" \
    --from-literal=DEBUG="false" \
    --from-literal=LOG_LEVEL="INFO" \
    --from-literal=KAILASH_RUNTIME="async" \
    --dry-run=client -o yaml | kubectl apply -f -

ok "Secret: ${SECRET_NAME}"

# ── Create configmap for deploy command ────────────────────
kubectl create configmap arbor-deploy-config \
    --namespace="${APP_NAMESPACE}" \
    --from-literal=domain="${ARBOR_DOMAIN}" \
    --from-literal=frontend-url="${FRONTEND_URL}" \
    --from-literal=api-url="${API_URL}" \
    --from-literal=arbor-version="${ARBOR_VERSION}" \
    --from-literal=registry-org="${REGISTRY_ORG}" \
    --from-literal=google-enabled="$([ -n "${GOOGLE_CLIENT_ID:-}" ] && echo true || echo false)" \
    --from-literal=tls-enabled="${TLS_ENABLED}" \
    --from-literal=cert-issuer="${CERT_ISSUER}" \
    --dry-run=client -o yaml | kubectl apply -f -

ok "ConfigMap: arbor-deploy-config"

# ── Capture summary flags before clearing secrets ──────────
SUMMARY_GOOGLE="$([ -n "${GOOGLE_CLIENT_ID:-}" ] && echo enabled || echo disabled)"
SUMMARY_AI="$([ -n "${OPENAI_API_KEY:-}" ] && echo 'server key' || echo 'BYOK only')"
SUMMARY_EMAIL="$([ -n "${SENDGRID_API_KEY:-}" ] && echo enabled || echo disabled)"

# ── Clear all secrets from shell memory ────────────────────
DB_PASSWORD=""; REDIS_PASSWORD=""; JWT_SECRET=""
SALARY_ENCRYPTION_KEY=""; LLM_KEY_ENCRYPTION_KEY=""
GOOGLE_CLIENT_SECRET=""; OPENAI_API_KEY=""; ANTHROPIC_API_KEY=""
SENDGRID_API_KEY=""; DATABASE_URL=""; REDIS_URL=""
unset DB_PASSWORD REDIS_PASSWORD JWT_SECRET \
      SALARY_ENCRYPTION_KEY LLM_KEY_ENCRYPTION_KEY \
      GOOGLE_CLIENT_SECRET OPENAI_API_KEY ANTHROPIC_API_KEY \
      SENDGRID_API_KEY DATABASE_URL REDIS_URL

# ── Summary ────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "${GREEN}  Configuration complete.${NC}"
echo ""
echo "  Namespace:    ${APP_NAMESPACE}"
echo "  Secrets:      ${SECRET_NAME}, ${DB_SECRET_NAME}"
echo "  Domain:       ${ARBOR_DOMAIN}"
echo "  Google SSO:   ${SUMMARY_GOOGLE}"
echo "  AI Advisory:  ${SUMMARY_AI}"
echo "  Email:        ${SUMMARY_EMAIL}"
echo "  TLS:          $([ "${TLS_ENABLED}" = "true" ] && echo "enabled (${CERT_ISSUER})" || echo "disabled")"
echo ""
echo "  Next step:    Run the deploy command to start Arbor:"
echo "    nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro \\"
echo "      terrenefoundation/arbor-build-toolkit:v1.2.0 deploy"
echo ""
echo "  To reconfigure, run this command again — it overwrites safely."
echo "============================================================"
