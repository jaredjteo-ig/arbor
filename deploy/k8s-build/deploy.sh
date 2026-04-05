#!/usr/bin/env bash
# ============================================================
# Arbor Build Toolkit — Deploy to Kubernetes
# ============================================================
#
# Applies all Arbor manifests to your cluster using the secrets
# created by configure.sh. Substitutes image tags and domain
# from the stored configuration.
#
# Usage:
#   ./deploy.sh                          # Deploy with configured settings
#   ./deploy.sh --namespace myns         # Custom namespace
#   ./deploy.sh --version v0.3.0         # Override image version
#
# Prerequisites:
#   - Run configure.sh first
#
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAMESPACE="arbor"
VERSION_OVERRIDE=""

# ── Parse flags ────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --namespace) APP_NAMESPACE="$2"; shift 2 ;;
        --version)   VERSION_OVERRIDE="$2"; shift 2 ;;
        *) echo "Unknown flag: $1"; exit 1 ;;
    esac
done

# ── Colors ─────────────────────────────────────────────────
if [ -t 1 ]; then
    RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
    BLUE='\033[0;34m'; NC='\033[0m'
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; NC=''
fi

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── Input validation ──────────────────────────────────────
validate() {
    local name="$1" value="$2" pattern="$3"
    if [[ ! "${value}" =~ ^${pattern}$ ]]; then
        fail "${name}='${value}' rejected. Allowed: ${pattern}"
    fi
}

validate "APP_NAMESPACE" "${APP_NAMESPACE}" '[a-zA-Z0-9._-]{1,63}'
if [[ -n "${VERSION_OVERRIDE}" ]]; then
    validate "VERSION_OVERRIDE" "${VERSION_OVERRIDE}" '[a-zA-Z0-9._-]{1,128}'
fi

# ── Preflight ──────────────────────────────────────────────
info "Checking prerequisites..."

kubectl get namespace "${APP_NAMESPACE}" >/dev/null 2>&1 \
    || fail "Namespace '${APP_NAMESPACE}' not found. Run 'configure' first."

kubectl get secret arbor-app-secrets -n "${APP_NAMESPACE}" >/dev/null 2>&1 \
    || fail "Secret 'arbor-app-secrets' not found. Run 'configure' first."

kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" >/dev/null 2>&1 \
    || fail "ConfigMap 'arbor-deploy-config' not found. Run 'configure' first."

ok "Configuration found in namespace '${APP_NAMESPACE}'"

# ── Read config from cluster ──────────────────────────────
ARBOR_DOMAIN=$(kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" \
    -o jsonpath='{.data.domain}')
REGISTRY_ORG=$(kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" \
    -o jsonpath='{.data.registry-org}')
ARBOR_VERSION=$(kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" \
    -o jsonpath='{.data.arbor-version}')
TLS_ENABLED=$(kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" \
    -o jsonpath='{.data.tls-enabled}' 2>/dev/null || echo "false")
CERT_ISSUER=$(kubectl get configmap arbor-deploy-config -n "${APP_NAMESPACE}" \
    -o jsonpath='{.data.cert-issuer}' 2>/dev/null || echo "letsencrypt-prod")

# Override version if specified
if [[ -n "${VERSION_OVERRIDE}" ]]; then
    ARBOR_VERSION="${VERSION_OVERRIDE}"
fi

info "Domain:   ${ARBOR_DOMAIN}"
info "Registry: ${REGISTRY_ORG}"
info "Version:  ${ARBOR_VERSION}"
info "TLS:      ${TLS_ENABLED}$([ "${TLS_ENABLED}" = "true" ] && echo " (issuer: ${CERT_ISSUER})" || true)"

# ── Check if pull secret is needed ─────────────────────────
if ! kubectl get secret arbor-pull-secret -n "${APP_NAMESPACE}" >/dev/null 2>&1; then
    warn "No imagePullSecret 'arbor-pull-secret' found."
    echo ""
    echo "  If your images are in a private registry, create a pull secret:"
    echo ""
    echo "    kubectl create secret docker-registry arbor-pull-secret \\"
    echo "      --namespace=${APP_NAMESPACE} \\"
    echo "      --docker-server=https://index.docker.io/v1/ \\"
    echo "      --docker-username=YOUR_USERNAME \\"
    echo "      --docker-password=YOUR_TOKEN"
    echo ""
    echo "  If your images are public, this is fine — continuing."
    echo ""
fi

# ── Apply manifests with substitution ──────────────────────
# Process each manifest: substitute placeholders, apply.
# Placeholders are validated config values — safe to interpolate.
MANIFEST_DIR="${SCRIPT_DIR}/app-manifests"

for manifest in postgres.yaml redis.yaml backend.yaml frontend.yaml ingress.yaml; do
    MANIFEST_PATH="${MANIFEST_DIR}/${manifest}"
    if [[ ! -f "${MANIFEST_PATH}" ]]; then
        fail "Missing manifest: ${MANIFEST_PATH}"
    fi

    info "Applying ${manifest}..."

    # TLS handling: if enabled, activate #TLS# lines; if disabled, remove them.
    if [[ "${TLS_ENABLED}" == "true" ]]; then
        TLS_SED=(-e 's|#TLS# ||')
    else
        TLS_SED=(-e '/#TLS#/d')
    fi

    sed \
        -e "s|REGISTRY_ORG|${REGISTRY_ORG}|g" \
        -e "s|ARBOR_VERSION|${ARBOR_VERSION}|g" \
        -e "s|ARBOR_DOMAIN|${ARBOR_DOMAIN}|g" \
        -e "s|CERT_ISSUER|${CERT_ISSUER}|g" \
        "${TLS_SED[@]}" \
        "${MANIFEST_PATH}" \
        | kubectl apply -n "${APP_NAMESPACE}" -f -
done

ok "All manifests applied"

# ── Wait for rollout ───────────────────────────────────────
info "Waiting for pods to start..."

echo ""
for deploy in arbor-postgres arbor-redis arbor-backend arbor-frontend; do
    info "  Waiting for ${deploy}..."
    if kubectl rollout status deployment "${deploy}" -n "${APP_NAMESPACE}" --timeout=120s 2>/dev/null; then
        ok "  ${deploy} is ready"
    else
        warn "  ${deploy} did not become ready within 120s"
        warn "  Check: kubectl describe deployment ${deploy} -n ${APP_NAMESPACE}"
    fi
done

# ── Health check ───────────────────────────────────────────
echo ""
info "Checking backend health..."

# Port-forward briefly to check health
HEALTH_PID=""
cleanup() { [ -n "${HEALTH_PID}" ] && kill "${HEALTH_PID}" 2>/dev/null || true; }
trap cleanup EXIT

kubectl port-forward svc/arbor-backend 18000:8000 -n "${APP_NAMESPACE}" >/dev/null 2>&1 &
HEALTH_PID=$!
sleep 3

if curl -sf http://localhost:18000/health >/dev/null 2>&1; then
    ok "Backend health check passed"
else
    warn "Backend health check failed (may still be starting)"
    warn "Check: kubectl logs -n ${APP_NAMESPACE} -l app.kubernetes.io/name=arbor-backend"
fi

kill "${HEALTH_PID}" 2>/dev/null || true
HEALTH_PID=""

# ── Summary ────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "${GREEN}  Arbor deployed to namespace '${APP_NAMESPACE}'${NC}"
echo ""
echo "  Backend:   ${REGISTRY_ORG}/arbor-backend:${ARBOR_VERSION}"
echo "  Frontend:  ${REGISTRY_ORG}/arbor-frontend:${ARBOR_VERSION}"
echo "  Domain:    https://${ARBOR_DOMAIN}"
echo ""
echo "  View pods:    kubectl get pods -n ${APP_NAMESPACE}"
echo "  View logs:    kubectl logs -n ${APP_NAMESPACE} -l app.kubernetes.io/name=arbor-backend"
echo "  View ingress: kubectl get ingress -n ${APP_NAMESPACE}"
echo ""
echo "  Make sure your DNS points ${ARBOR_DOMAIN} to your"
echo "  ingress controller's external IP."
echo "============================================================"
