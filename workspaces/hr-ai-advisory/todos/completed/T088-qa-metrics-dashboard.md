# T088 — QA Metrics Dashboard (Frontend)

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: MEDIUM
**Estimated Effort**: 5h
**Dependencies**: T083, T084, T085, T087

## What to build

A dedicated metrics view in the admin panel that shows quality trends over time, per-dimension performance, failure pattern analysis, patch history, and KB gap detection. This gives the team operational visibility into advisory quality — whether it is improving, which areas need attention, and whether patches are working.

## Acceptance Criteria

### Composite Quality Score Chart

- [ ] Time-series line chart: average overall quality score per QA session (x-axis = session date, y-axis = 1-5)
- [ ] Target line at 3.5 (quality floor) shown as dashed reference
- [ ] Sessions shown as data points; tooltip shows session date, reviewer, count evaluated

### Per-Dimension Trend Chart

- [ ] 8 lines, one per dimension, showing trend over sessions
- [ ] Dimensions toggleable (show/hide per dimension)
- [ ] Highlight dimensions below 3.5 in amber/red

### Failure Pattern Heatmap

- [ ] Grid: affected_agent (rows) x failure_category (columns)
- [ ] Cell colour intensity = frequency of that combination in QA evaluations
- [ ] Clicking a cell shows the list of evaluations in that cluster
- [ ] Cells with open patches shown with a patch icon

### Patch History Table

- [ ] All patches listed: target agent, patch type, status badge, proposed date, score delta (before/after), approved by
- [ ] Status filter: all, approved, rejected, rolled_back, deployed
- [ ] Clicking a patch shows: proposed text, evidence evaluations, test results, regression outcome
- [ ] Score delta shown as +X.X (green) or -X.X (red)

### KB Gap Detector

- [ ] Shows topics with consistently low citation quality scores (citation_quality dimension < 3.0 across >= 3 evaluations)
- [ ] Groups by domain/agent to show which KB areas are thin
- [ ] Links to KB Management tab to add provisions (T082 type gaps)

## Files

- `apps/web/src/components/admin/QAMetricsDashboard.tsx` — new component (main dashboard)
- `apps/web/src/components/admin/QualityTrendChart.tsx` — composite score chart
- `apps/web/src/components/admin/DimensionTrendChart.tsx` — per-dimension chart
- `apps/web/src/components/admin/FailureHeatmap.tsx` — agent x category heatmap
- `apps/web/src/components/admin/PatchHistoryTable.tsx` — patch list and detail
- `apps/web/src/components/admin/KBGapDetector.tsx` — gap analysis view
- `apps/web/src/pages/admin/index.tsx` — add QA Metrics tab

## Reference

12-human-qa-workflow-design.md Section 5 (Metrics Dashboard)

## Definition of Done

- [ ] All 5 dashboard sections render with real data from the QA API
- [ ] Charts use recharts or equivalent (consistent with existing design system)
- [ ] Failure heatmap drill-down works (click cell → see evaluations)
- [ ] Patch history score delta correctly calculated and coloured
- [ ] KB Gap Detector correctly identifies domains with low citation scores
- [ ] Dashboard loads in < 2 seconds (no unbounded data fetching)
