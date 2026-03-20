# Deployment: Shadow Agent (2026-03-20)

## Summary

Deployed Shadow Agent intelligence layer (M61-M65) to production.

## Changes Deployed

- **Backend**: 12 shadow agent modules (`src/hr_advisory/shadow/`), 13 API endpoints under `/shadow/`
- **Frontend**: 9 React components (`shadow-agent/`), context polling with 403 backoff
- **Tests**: 465 tests across 10 files, 0 failures
- **Security**: 3 red team rounds, 25 findings, all resolved
- **Codification**: New agent, skill, authority doc for shadow agent knowledge
- **Config**: Removed stale AWS references, updated runbook to GCP

## Commits (18 total since last deploy)

- `1d3a51a` fix(shadow): add type annotation to ArborHistory map destructure
- `56cbc3a` fix(deploy): remove AWS references, update runbook to GCP
- `2d7262c` feat(shadow): codify shadow agent knowledge + fix context polling on 403
- `dd719de` docs(deploy): BYOK API key decision
- `19c44e4` test(shadow): red team hardening, comprehensive test coverage (465 tests)
- `f163c11` feat(shadow): frontend gap closure — ArborOverlay, ArborResult, ArborHistory
- `00192a6` feat(shadow): gap closure — entity resolver, workflow composer, observation, memory
- `3647369` feat: Arbor frontend integration — CommandSurface, PaceCard, shadow API (M63)
- Plus 10 earlier commits (M61-M62, scope guard, classifier)

## Verification

- Health check: 200 OK (all workflows healthy)
- Frontend: 200 OK
- Shadow endpoint: 401 (auth required — correct, endpoint exists)
- All containers healthy (backend, frontend, caddy, postgres, redis)
- SDK packages at latest versions (kailash 1.0.0, dataflow 1.0.1, nexus 1.4.2, kaizen 1.3.0)

## Pre-existing Issues (not introduced by this deploy)

- 115 test failures in learning, QA, invitation, feedback modules (test ordering / state pollution)
- All 465 shadow agent tests pass in isolation and together

## Infrastructure

- Target: GCE `arbor-prod` (asia-southeast1-b, terrene-care project)
- Method: rsync + docker compose rebuild
- Git remote: Updated from `esperie/aite` to `terrene-foundation/arbor`
