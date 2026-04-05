#!/usr/bin/env bash
# ============================================================
# Arbor Build System — Build & Push Container Image
# ============================================================
#
# Builds a container image inside Kubernetes using Kaniko
# (no Docker daemon required). Pushes to your configured registry.
#
# Usage:
#   ./build.sh backend v0.3.0              # Build backend image
#   ./build.sh frontend v0.3.0             # Build frontend image
#   ./build.sh backend v0.3.0 my-org       # Push to my-org/ prefix
#
# Prerequisites:
#   - Run setup.sh first (one-time)
#   - kubectl configured and pointing to your cluster
#
# ============================================================
set -euo pipefail

# ── Configuration ──────────────────────────────────────────
NAMESPACE="arbor-build"
GIT_REPO="https://github.com/terrene-foundation/arbor.git"
GIT_REF="${GIT_REF:-main}"
DEFAULT_ORG="terrenefoundation"

# Kaniko executor — pinned by digest for supply chain safety.
# Tag v1.23.2 digest retrieved 2026-03-31 from gcr.io.
# To update: TOKEN=$(curl -sf "https://gcr.io/v2/token?scope=repository:kaniko-project/executor:pull&service=gcr.io" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])") && curl -sI "https://gcr.io/v2/kaniko-project/executor/manifests/vX.Y.Z" -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.oci.image.index.v1+json" | grep docker-content-digest
KANIKO_IMAGE="gcr.io/kaniko-project/executor:v1.23.2@sha256:9e69fd4330ec887829c780f5126dd80edc663df6def362cd22e79bcdf00ac53f"

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

# ── Usage ──────────────────────────────────────────────────
usage() {
    echo "Usage: $0 <component> <tag> [registry-org]"
    echo ""
    echo "  component    backend | frontend"
    echo "  tag          Image tag (e.g., v0.3.0, latest)"
    echo "  registry-org Docker Hub org/user (default: ${DEFAULT_ORG})"
    echo ""
    echo "Examples:"
    echo "  $0 backend v0.3.0"
    echo "  $0 frontend v0.3.0 mycompany"
    echo ""
    echo "Environment:"
    echo "  GIT_REF      Git branch/tag to build from (default: main)"
    exit 1
}

# ── Input validation (anti-injection) ─────────────────────
# Every user-controlled value is validated against a strict
# allowlist regex BEFORE it touches any kubectl command or YAML.
# This prevents argument injection via crafted inputs.
validate() {
    local name="$1" value="$2" pattern="$3"
    if [[ ! "${value}" =~ ^${pattern}$ ]]; then
        fail "${name}='${value}' rejected. Allowed pattern: ${pattern}"
    fi
}

COMPONENT="${1:-}"
TAG="${2:-}"
REGISTRY_ORG="${3:-${DEFAULT_ORG}}"

if [[ -z "${COMPONENT}" || -z "${TAG}" ]]; then
    usage
fi

# Strict validation — only safe characters
validate "COMPONENT"    "${COMPONENT}"    '(backend|frontend)'
validate "TAG"          "${TAG}"          '[a-zA-Z0-9._-]{1,128}'
validate "REGISTRY_ORG" "${REGISTRY_ORG}" '[a-zA-Z0-9._-]{1,128}'
validate "GIT_REF"      "${GIT_REF}"      '[a-zA-Z0-9._/-]{1,128}'

# ── Resolve Dockerfile and image name ─────────────────────
case "${COMPONENT}" in
    backend)
        DOCKERFILE="deploy/Dockerfile.backend"
        IMAGE_NAME="arbor-backend"
        BUILD_ARGS=""
        ;;
    frontend)
        DOCKERFILE="deploy/Dockerfile.frontend"
        IMAGE_NAME="arbor-frontend"
        # Frontend build args — read from env or prompt
        API_URL="${NEXT_PUBLIC_API_URL:-}"
        GOOGLE_CLIENT_ID="${NEXT_PUBLIC_GOOGLE_CLIENT_ID:-}"
        if [[ -z "${API_URL}" ]]; then
            echo ""
            read -rp "NEXT_PUBLIC_API_URL (e.g., https://arbor.example.com/api): " API_URL
            if [[ -z "${API_URL}" ]]; then
                fail "API URL is required for frontend builds."
            fi
        fi
        # Validate URL format (https only, no shell metacharacters)
        validate "API_URL" "${API_URL}" 'https://[a-zA-Z0-9._:/-]+'
        if [[ -n "${GOOGLE_CLIENT_ID}" ]]; then
            validate "GOOGLE_CLIENT_ID" "${GOOGLE_CLIENT_ID}" '[a-zA-Z0-9._-]+'
        fi
        BUILD_ARGS="--build-arg=NEXT_PUBLIC_API_URL=${API_URL}"
        if [[ -n "${GOOGLE_CLIENT_ID}" ]]; then
            BUILD_ARGS="${BUILD_ARGS} --build-arg=NEXT_PUBLIC_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}"
        fi
        ;;
esac

FULL_IMAGE="${REGISTRY_ORG}/${IMAGE_NAME}:${TAG}"

# ── Preflight checks ──────────────────────────────────────
info "Checking prerequisites..."

kubectl get ns "${NAMESPACE}" >/dev/null 2>&1 \
    || fail "Namespace '${NAMESPACE}' not found. Run setup.sh first."

kubectl get secret registry-credentials -n "${NAMESPACE}" >/dev/null 2>&1 \
    || fail "Secret 'registry-credentials' not found. Run setup.sh first."

ok "Build system ready"

# ── Generate unique job name ───────────────────────────────
# Truncate to fit K8s 63-char name limit
TIMESTAMP="$(date +%s)"
JOB_NAME="arbor-build-${COMPONENT}-$(echo "${TAG}" | tr '.' '-' | cut -c1-20)-${TIMESTAMP}"
JOB_NAME="$(echo "${JOB_NAME}" | cut -c1-63)"

info "Building ${FULL_IMAGE}"
info "Dockerfile: ${DOCKERFILE}"
info "Source: ${GIT_REPO}#${GIT_REF}"
info "Job: ${JOB_NAME}"

# ── Build Kaniko args array ────────────────────────────────
# Constructed safely — each arg is a separate YAML list item,
# never concatenated into a shell string.
KANIKO_ARGS_YAML="            - \"--dockerfile=${DOCKERFILE}\"
            - \"--context=git://${GIT_REPO}#refs/heads/${GIT_REF}\"
            - \"--destination=${FULL_IMAGE}\"
            - \"--cache=true\"
            - \"--cache-ttl=24h\"
            - \"--snapshot-mode=redo\"
            - \"--use-new-run\""

# Add build args for frontend
if [[ "${COMPONENT}" == "frontend" ]]; then
    KANIKO_ARGS_YAML="${KANIKO_ARGS_YAML}
            - \"--build-arg=NEXT_PUBLIC_API_URL=${API_URL}\""
    if [[ -n "${GOOGLE_CLIENT_ID:-}" ]]; then
        KANIKO_ARGS_YAML="${KANIKO_ARGS_YAML}
            - \"--build-arg=NEXT_PUBLIC_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}\""
    fi
fi

# ── Create and apply Job manifest ──────────────────────────
# The manifest is generated from a heredoc with validated values.
# All user inputs were validated above — no raw interpolation.
cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: ${JOB_NAME}
  namespace: ${NAMESPACE}
  labels:
    app: arbor-kaniko-build
    component: ${COMPONENT}
    version: "${TAG}"
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: arbor-kaniko-build
        component: ${COMPONENT}
    spec:
      serviceAccountName: arbor-builder
      restartPolicy: Never
      containers:
        - name: kaniko
          image: ${KANIKO_IMAGE}
          args:
${KANIKO_ARGS_YAML}
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          volumeMounts:
            - name: docker-config
              mountPath: /kaniko/.docker
              readOnly: true
      volumes:
        - name: docker-config
          secret:
            secretName: registry-credentials
            items:
              - key: .dockerconfigjson
                path: config.json
EOF

ok "Build job created"

# ── Stream logs and wait ───────────────────────────────────
info "Waiting for build pod to start..."

# Wait for the pod to be created (up to 120s for image pull)
RETRIES=0
MAX_RETRIES=24
POD_NAME=""
while [[ -z "${POD_NAME}" && ${RETRIES} -lt ${MAX_RETRIES} ]]; do
    POD_NAME=$(kubectl get pods -n "${NAMESPACE}" \
        -l "job-name=${JOB_NAME}" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [[ -z "${POD_NAME}" ]]; then
        sleep 5
        RETRIES=$((RETRIES + 1))
    fi
done

if [[ -z "${POD_NAME}" ]]; then
    fail "Build pod did not start within 120s. Check: kubectl describe job ${JOB_NAME} -n ${NAMESPACE}"
fi

ok "Build pod: ${POD_NAME}"
info "Streaming build logs (Ctrl+C to detach — build continues in cluster)..."
echo ""

# Stream logs — follows until pod completes
kubectl logs -f "${POD_NAME}" -n "${NAMESPACE}" 2>/dev/null || true

# ── Check result ───────────────────────────────────────────
echo ""
JOB_STATUS=$(kubectl get job "${JOB_NAME}" -n "${NAMESPACE}" \
    -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' 2>/dev/null || true)

JOB_FAILED=$(kubectl get job "${JOB_NAME}" -n "${NAMESPACE}" \
    -o jsonpath='{.status.conditions[?(@.type=="Failed")].status}' 2>/dev/null || true)

if [[ "${JOB_STATUS}" == "True" ]]; then
    echo ""
    echo "============================================================"
    echo -e "${GREEN}  Build succeeded: ${FULL_IMAGE}${NC}"
    echo ""
    echo "  To deploy, update your manifests to use this image:"
    echo "    image: ${FULL_IMAGE}"
    echo ""
    echo "  Or pull it locally:"
    echo "    nerdctl pull ${FULL_IMAGE}"
    echo "============================================================"
elif [[ "${JOB_FAILED}" == "True" ]]; then
    echo ""
    fail "Build failed. Check logs: kubectl logs job/${JOB_NAME} -n ${NAMESPACE}"
else
    warn "Build status unclear (you may have detached). Check:"
    warn "  kubectl get job ${JOB_NAME} -n ${NAMESPACE}"
    warn "  kubectl logs job/${JOB_NAME} -n ${NAMESPACE}"
fi
