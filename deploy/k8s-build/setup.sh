#!/usr/bin/env bash
# ============================================================
# Arbor Build System — One-Time Setup
# ============================================================
#
# Run this script on your Kubernetes cluster to set up the
# build system. It creates a dedicated namespace, security
# policies, and stores your registry credentials securely.
#
# Your credentials NEVER leave your cluster.
#
# Prerequisites:
#   - kubectl configured and pointing to your cluster
#   - Cluster admin or namespace-create permissions
#   - A Docker Hub account with an access token
#
# Usage:
#   chmod +x setup.sh
#   ./setup.sh
#
# To create a Docker Hub access token:
#   1. Log in to https://hub.docker.com
#   2. Go to Account Settings > Security > Access Tokens
#   3. Click "New Access Token"
#   4. Name: "arbor-build" (or any descriptive name)
#   5. Permissions: "Read & Write"
#   6. Copy the generated token (you won't see it again)
#
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAMESPACE="arbor-build"

# ── Colors (disable if not a terminal) ─────────────────────
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

# ── Preflight checks ──────────────────────────────────────
info "Checking prerequisites..."

command -v kubectl >/dev/null 2>&1 || fail "kubectl not found. Install it first."

kubectl cluster-info >/dev/null 2>&1 || fail "Cannot reach Kubernetes cluster. Check your kubeconfig."

ok "kubectl connected to cluster"

# ── Apply manifests ────────────────────────────────────────
info "Creating namespace and security policies..."

kubectl apply -f "${SCRIPT_DIR}/manifests/00-namespace.yaml"
kubectl apply -f "${SCRIPT_DIR}/manifests/01-rbac.yaml"
kubectl apply -f "${SCRIPT_DIR}/manifests/02-network-policy.yaml"
kubectl apply -f "${SCRIPT_DIR}/manifests/03-resource-quota.yaml"

ok "Namespace '${NAMESPACE}' created with RBAC, network policy, and resource quota"

# ── Registry type selection ────────────────────────────────
echo ""
echo "Which container registry will you use?"
echo ""
echo "  1) Docker Hub          (hub.docker.com)"
echo "  2) GitHub Container    (ghcr.io)"
echo "  3) Other               (custom registry URL)"
echo ""
read -rp "Choice [1/2/3]: " REGISTRY_CHOICE

case "${REGISTRY_CHOICE}" in
    1)
        REGISTRY_SERVER="https://index.docker.io/v1/"
        REGISTRY_LABEL="Docker Hub"
        ;;
    2)
        REGISTRY_SERVER="https://ghcr.io"
        REGISTRY_LABEL="GitHub Container Registry"
        ;;
    3)
        echo ""
        read -rp "Registry URL (e.g., registry.example.com): " CUSTOM_REGISTRY
        if [[ -z "${CUSTOM_REGISTRY}" ]]; then
            fail "Registry URL cannot be empty."
        fi
        # Normalize: add https:// if missing
        if [[ ! "${CUSTOM_REGISTRY}" =~ ^https?:// ]]; then
            REGISTRY_SERVER="https://${CUSTOM_REGISTRY}"
        else
            REGISTRY_SERVER="${CUSTOM_REGISTRY}"
        fi
        REGISTRY_LABEL="${REGISTRY_SERVER}"
        ;;
    *)
        fail "Invalid choice. Run setup.sh again."
        ;;
esac

ok "Using ${REGISTRY_LABEL}"

# ── Collect credentials (stdin, not args — args leak to /proc) ──
echo ""
info "Enter your registry credentials."
info "These are stored ONLY in your cluster's etcd (as a Kubernetes Secret)."
info "They are never sent anywhere else."
echo ""

read -rp  "Username: " REG_USER
read -rsp "Access token (hidden): " REG_TOKEN
echo ""

# ── Validate inputs ────────────────────────────────────────
if [[ -z "${REG_USER}" ]]; then
    fail "Username cannot be empty."
fi
if [[ -z "${REG_TOKEN}" ]]; then
    fail "Access token cannot be empty."
fi
# Username: alphanumeric, hyphens, underscores, dots (Docker Hub format)
if [[ ! "${REG_USER}" =~ ^[a-zA-Z0-9._-]+$ ]]; then
    fail "Username contains invalid characters. Only letters, numbers, dots, hyphens, underscores."
fi
# Token: printable ASCII, no shell metacharacters
if [[ "${REG_TOKEN}" =~ [\;\|\&\>\<\`\$\(\)] ]]; then
    fail "Token contains shell metacharacters. This looks wrong — check your token."
fi

# ── Create the Kubernetes secret ───────────────────────────
info "Storing credentials in ${NAMESPACE}/registry-credentials..."

kubectl create secret docker-registry registry-credentials \
    --namespace="${NAMESPACE}" \
    --docker-server="${REGISTRY_SERVER}" \
    --docker-username="${REG_USER}" \
    --docker-password="${REG_TOKEN}" \
    --dry-run=client -o yaml | kubectl apply -f -

# ── Clear credentials from shell memory ────────────────────
REG_USER=""; REG_TOKEN=""
unset REG_USER REG_TOKEN

ok "Credentials stored in cluster"

# ── Store registry config for build.sh ─────────────────────
# Save the registry server (not credentials) so build.sh knows where to push.
# This is non-secret metadata.
kubectl create configmap build-config \
    --namespace="${NAMESPACE}" \
    --from-literal=registry-server="${REGISTRY_SERVER}" \
    --from-literal=registry-label="${REGISTRY_LABEL}" \
    --dry-run=client -o yaml | kubectl apply -f -

ok "Build config saved"

# ── Verify ─────────────────────────────────────────────────
echo ""
info "Verifying setup..."

SECRET_EXISTS=$(kubectl get secret registry-credentials -n "${NAMESPACE}" -o name 2>/dev/null || true)
if [[ -z "${SECRET_EXISTS}" ]]; then
    fail "Secret was not created. Check cluster permissions."
fi

ok "Secret exists: ${SECRET_EXISTS}"

NS_STATUS=$(kubectl get ns "${NAMESPACE}" -o jsonpath='{.status.phase}' 2>/dev/null || true)
if [[ "${NS_STATUS}" != "Active" ]]; then
    fail "Namespace is not active: ${NS_STATUS}"
fi

ok "Namespace is active"

# ── Done ───────────────────────────────────────────────────
echo ""
echo "============================================================"
echo -e "${GREEN}  Setup complete.${NC}"
echo ""
echo "  Namespace:   ${NAMESPACE}"
echo "  Registry:    ${REGISTRY_LABEL}"
echo "  Secret:      registry-credentials"
echo ""
echo "  Next step:   ./build.sh backend v0.3.0"
echo "============================================================"
