# T035 — Compliance Health Check (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Backend** (pure deterministic function):

- `ComplianceCheckInput` with company_size, has_foreign_workers, sector, and 8 boolean compliance flags
- `ComplianceFinding` (domain, issue, severity, recommendation, provision_id, deadline)
- `InspectionItem` for MOM inspection readiness (category, item, status: pass/fail/unknown, provision)
- `ComplianceCheckResult` (score, risk_tier, findings, action_items, domains_checked, explanation, inspection_readiness)
- 10 compliance checks covering EA, CPF, WSH, TGFEP, TG-FWAR, EFMA
- Score calculation: 100 base minus deductions (critical:-20, high:-10, medium:-5, low:-2)
- MOM inspection readiness checklist with 9 items across 5 categories

**React**:

- Client-side compliance checker mirroring backend logic
- Checklist form with 8 compliance items + company size + foreign worker toggle
- Results view: score gauge with circular indicator, RiskTierBadge, findings grouped by severity
- Tabs: Findings (severity badges, recommendations, SourceCitation, action items) and MOM Inspection Readiness
- "Run Another Check" reset flow

**Flutter**:

- Full compliance screen replacing placeholder (1277 lines)
- ChecklistForm with company profile section and compliance items
- ResultsView with DefaultTabController and two tabs
- ScoreCard with circular CustomPaint indicator
- FindingsTab grouped by severity with FindingCards
- InspectionTab with pass/fail/unknown icons per category
- Zero Flutter analysis issues

## Files

- `src/hr_advisory/workflows/compliance_checker.py` — backend compliance check engine
- `apps/web/src/app/(dashboard)/compliance/page.tsx` — React compliance page
- `apps/mobile/lib/features/compliance/screens/compliance_screen.dart` — Flutter compliance screen
