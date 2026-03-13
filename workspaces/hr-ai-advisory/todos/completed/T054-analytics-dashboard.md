# T054 — Analytics Dashboard

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Analytics Models**:

- `WorkforceAnalytics` with breakdowns by nationality, employment type, pass type, and department — provides full workforce composition visibility
- `ComplianceMetrics` with trend tracking and per-domain scores — tracks compliance posture over time
- `CostProjection` with CPF and levy line items — projects employer cost obligations
- `UsageMetrics` with queries by domain, top queries, and feedback rate — tracks platform adoption and satisfaction

**Public API**:

- `get_workforce_analytics()` — generates workforce composition breakdowns from employee records
- `get_compliance_metrics()` — calculates compliance scores across all regulatory domains with trend data
- `get_cost_projection()` — projects CPF contributions and foreign worker levy costs
- `get_usage_metrics()` — aggregates platform usage data including query patterns and feedback rates

**Frontend — React**:

- Analytics dashboard page at `apps/web/src/app/(dashboard)/analytics/page.tsx` — interactive charts and summary cards for workforce, compliance, cost, and usage data

**Frontend — Flutter**:

- Analytics screen at `apps/mobile/lib/features/analytics/screens/analytics_screen.dart` — mobile-optimised analytics views with the same data dimensions

## Files

- `src/hr_advisory/analytics/engine.py` — analytics engine module
- `src/hr_advisory/analytics/__init__.py` — package init
- `apps/web/src/app/(dashboard)/analytics/page.tsx` — React analytics page
- `apps/mobile/lib/features/analytics/screens/analytics_screen.dart` — Flutter analytics screen
