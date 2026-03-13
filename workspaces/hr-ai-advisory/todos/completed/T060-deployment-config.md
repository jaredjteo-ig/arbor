# T060 — Deployment Configuration

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Docker — Backend**:

- `Dockerfile.backend` — Python 3.11-slim base, AsyncLocalRuntime for container compatibility, non-root user for security, health check endpoint, optimised layer caching

**Docker — Frontend**:

- `Dockerfile.frontend` — Node 20 Alpine base, multi-stage build (deps, build, runtime), minimised production image size

**Compose — Production**:

- `docker-compose.prod.yml` — full stack orchestration with 4 services:
  - Backend (Python API)
  - Frontend (Next.js)
  - PostgreSQL (persistent volume)
  - Redis (caching layer)
- Health checks, restart policies, and network isolation configured

**Deployment Documentation**:

- `deployment-config.md` — comprehensive deployment runbook covering:
  - Architecture diagram and service dependencies
  - Required environment variables with descriptions
  - Health check endpoints and expected responses
  - Backup and recovery procedures for PostgreSQL
  - Monitoring setup (metrics, alerting thresholds)
  - Rollback procedure (versioned images, database migration rollback)

## Files

- `deploy/Dockerfile.backend` — backend container image
- `deploy/Dockerfile.frontend` — frontend container image
- `deploy/docker-compose.prod.yml` — production compose orchestration
- `deploy/deployment-config.md` — deployment runbook
