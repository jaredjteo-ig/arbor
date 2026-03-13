# T040 — Regulatory Change Management Pipeline

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Backend — Regulatory Update Workflow**:

- `RegulatoryUpdate` data model with full lifecycle: Draft → In Review → Approved/Rejected → Published
- `AffectedProvision` for tracking which provisions change (current text, new text, change type)
- `UpdateStatus` enum (draft, in_review, approved, rejected, published)
- `UpdateUrgency` enum (critical, high, medium, low)
- State transition functions: `create_update()`, `submit_for_review()`, `approve_update()`, `reject_update()`, `publish_update()`
- Human-in-the-loop validation gate at the approve/reject step

**Backend — Staleness Tracking**:

- `StalenessRecord` for tracking provision review dates
- `record_review()`, `get_stale_provisions()`, `get_staleness_summary()`
- Automated detection of provisions past their next_review_date

**API — Admin Router**:

- POST/GET `/admin/updates` — CRUD for regulatory updates
- POST `/admin/updates/{id}/submit` — submit for review
- POST `/admin/updates/{id}/approve` — approve (human gate)
- POST `/admin/updates/{id}/reject` — reject with notes
- POST `/admin/updates/{id}/publish` — publish and generate alerts
- GET `/admin/staleness/summary` — staleness overview
- GET `/admin/staleness/stale` — list stale provisions
- POST `/admin/staleness/review` — record provision review
- GET `/admin/metrics` — platform metrics for admin dashboard

## Files

- `src/hr_advisory/workflows/regulatory_updates.py` — regulatory update pipeline
- `src/hr_advisory/api/routers/admin.py` — admin API endpoints
- `src/hr_advisory/api/routers/__init__.py` — registered admin_router
