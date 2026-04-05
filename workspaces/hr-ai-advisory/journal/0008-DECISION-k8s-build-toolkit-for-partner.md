---
type: DECISION
date: 2026-03-31
created_at: 2026-03-31T20:45:00+08:00
author: co-authored
session_turn: 1
project: arbor
topic: Kaniko-based build toolkit for containerd-only partner clusters
phase: implement
tags: [deployment, kubernetes, kaniko, partner, security, docker-hub]
---

# K8s Build Toolkit for Partner Deployment

## Context

Partner runs Kubernetes with containerd as the container runtime. Installing Docker Engine alongside containerd causes cgroup/namespace conflicts. They cannot run `docker build` on their cluster nodes. We need a way for them to build and deploy Arbor images without Docker.

## Decision

Built a self-contained Docker Hub image (`terrenefoundation/arbor-build-toolkit:v1.2.0`) that packages:

- **setup.sh** — creates isolated `arbor-build` namespace with RBAC, NetworkPolicy, ResourceQuota; stores registry credentials as K8s Secret
- **configure.sh** — creates `arbor` namespace with all app secrets (auto-generates DB/Redis/JWT/encryption keys; prompts only for external creds like Google OAuth, OpenAI)
- **build.sh** — launches Kaniko Jobs in-cluster that build from Dockerfile and push to registry
- **deploy.sh** — applies K8s manifests (Postgres, Redis, backend, frontend, ingress) with config substitution

Partner runs everything via `nerdctl run` with kubeconfig mounted read-only. Their credentials never leave their cluster.

## Alternatives Considered

1. **nerdctl build** on nodes — requires node SSH access and `nerdctl` installed; not available on all managed K8s
2. **BuildKit daemon** — requires a persistent deployment in cluster; more moving parts
3. **Buildah** — requires privileged containers on some runtimes; security concern
4. **Ship raw scripts** — file transfer logistics; no versioning; partner must have correct tools installed

Kaniko chosen because: runs as unprivileged K8s Job (no daemon, no socket, no root), builds standard Dockerfiles unchanged, pushes directly to registry, well-maintained by Google.

## Security Properties

- All inputs validated against strict regex allowlists (anti-injection)
- Credentials read from stdin, not CLI args (invisible to `/proc`)
- Build pods restricted to egress port 443 only (NetworkPolicy)
- ResourceQuota prevents builds from starving production workloads
- Kaniko executor digest-pinned (`@sha256:...`) for supply chain safety
- Auto-generated crypto uses OpenSSL (not pseudo-random)
- Re-run safe: detects existing secrets, asks before regenerating passwords
- TLS via cert-manager: configurable with `#TLS#` marker system in ingress

## Tested

Full flow tested against kind v0.31.0 (K8s v1.35.0): setup, configure, deploy all passed. Backend health check passed via port-forward. One bug found and fixed (unbound variable in summary after secret cleanup).

## For Discussion

1. The Kaniko executor image is pinned to `v1.23.2` but without a digest hash — should we pin by `@sha256:...` to fully prevent tag mutation attacks, and what's the update process when Kaniko releases security patches?
2. If the partner had used a managed K8s service (GKE/EKS/AKS) instead of bare-metal containerd, would Workload Identity (Tier 3) have been the better first recommendation? What signals should determine the tier choice?
3. The `configure.sh` auto-generates new DB/Redis passwords on every re-run — if the partner re-configures after data exists, the new password won't match the running Postgres. Should we detect existing secrets and offer "keep existing" vs "regenerate"?
