#!/usr/bin/env bash
# ============================================================
# Arbor Build Toolkit — Entrypoint
# ============================================================
# Dispatches to setup.sh or build.sh based on the first argument.
# All inputs are validated in the target scripts — this is just routing.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Verify kubectl connectivity ────────────────────────────
check_kube() {
    if ! kubectl cluster-info >/dev/null 2>&1; then
        echo ""
        echo "ERROR: Cannot reach Kubernetes cluster."
        echo ""
        echo "Mount your kubeconfig when running this container:"
        echo ""
        echo "  nerdctl run -it --rm \\"
        echo "    -v ~/.kube:/home/toolkit/.kube:ro \\"
        echo "    terrenefoundation/arbor-build-toolkit $*"
        echo ""
        exit 1
    fi
}

IMG="terrenefoundation/arbor-build-toolkit"

case "${1:-help}" in
    setup)
        check_kube setup
        shift
        exec "${SCRIPT_DIR}/setup.sh" "$@"
        ;;
    configure)
        check_kube configure
        shift
        exec "${SCRIPT_DIR}/configure.sh" "$@"
        ;;
    build)
        check_kube build
        shift
        exec "${SCRIPT_DIR}/build.sh" "$@"
        ;;
    deploy)
        check_kube deploy
        shift
        exec "${SCRIPT_DIR}/deploy.sh" "$@"
        ;;
    help|--help|-h)
        echo ""
        echo "Arbor Build Toolkit — Build & deploy Arbor on Kubernetes (no Docker needed)"
        echo ""
        echo "Usage:"
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro \\"
        echo "    ${IMG} <command> [args...]"
        echo ""
        echo "Commands:"
        echo "  setup                       Set up build namespace + registry credentials"
        echo "  configure                   Set up app namespace + all application secrets"
        echo "  build <component> <tag>     Build an image (backend | frontend)"
        echo "  deploy                      Deploy Arbor to your cluster"
        echo "  help                        Show this message"
        echo ""
        echo "Typical flow (first time):"
        echo ""
        echo "  1. setup      — build system + Docker Hub token"
        echo "  2. configure  — app secrets (DB, Redis, JWT, Google, OpenAI)"
        echo "  3. build      — build backend + frontend images"
        echo "  4. deploy     — apply K8s manifests and start Arbor"
        echo ""
        echo "Examples:"
        echo ""
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro ${IMG} setup"
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro ${IMG} configure"
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro ${IMG} build backend v0.3.0"
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro ${IMG} build frontend v0.3.0"
        echo "  nerdctl run -it --rm -v ~/.kube:/home/toolkit/.kube:ro ${IMG} deploy"
        echo ""
        ;;
    version|--version|-v)
        echo "arbor-build-toolkit v1.2.0"
        ;;
    *)
        echo "Unknown command: $1"
        echo "Run with 'help' for usage."
        exit 1
        ;;
esac
