# T092 — Remove Hardcoded Data and Seed Demo State

**Status**: ACTIVE
**Milestone**: 10 — Demo-Ready First Impressions
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T029, T038, T089

## What to build

Remove the hardcoded `notificationCount={3}` from AppShell and wire the notification badge to real data (or suppress the badge when zero). Then seed the dashboard with realistic sample data that new users can see immediately, without requiring a completed company profile. This sample data is clearly labelled as illustrative and shows the value Arbor delivers: sample compliance domain scores, a sample regulatory alert, and a sample advisory conversation preview. The goal is to eliminate the "empty product" impression on first login.

## Acceptance Criteria

### Notification Count Fix

- [ ] Remove hardcoded `notificationCount={3}` from AppShell
- [ ] Connect notification count to the real notifications/alerts API endpoint
- [ ] Show no badge (or badge with 0 hidden) when there are zero notifications
- [ ] Badge count updates without requiring page refresh (on mount)

### Sample Compliance Domains

- [ ] New users see 3-4 sample compliance domain cards on the dashboard (e.g., Employment Act, CPF, Leave Management)
- [ ] Sample cards are labelled clearly with "Sample data — complete your profile to see your score"
- [ ] Sample scores use realistic values (not 0% or 100%) that show the score system meaningfully
- [ ] Sample cards are replaced with real data once the company profile is created

### Sample Regulatory Alert

- [ ] One sample regulatory alert card is shown in the dashboard alert section for new users
- [ ] Alert references a real, recent regulatory update (e.g., CPF salary ceiling change)
- [ ] Labelled as a sample with a prompt to enable alerts after profile setup

### Sample Advisory Preview

- [ ] A "What Arbor can answer" preview card shows a realistic Q&A pair
  - Example Q: "Do I need to give notice pay for resignations during probation?"
  - Example A: Truncated answer showing 2-3 lines + "Ask Arbor your question" button
- [ ] Clicking the button navigates to /advisory

## Files

- `apps/web/src/components/shell/AppShell.tsx` — remove hardcoded notification count, wire to API
- `apps/web/src/app/(dashboard)/page.tsx` — add sample compliance cards, alert, and advisory preview
- `apps/web/src/components/dashboard/SampleComplianceDomains.tsx` — new component
- `apps/web/src/components/dashboard/SampleAdvisoryPreview.tsx` — new component

## Definition of Done

- [ ] No hardcoded notification count in codebase
- [ ] Notification badge reflects real data and disappears when count is zero
- [ ] New user dashboard shows labelled sample compliance cards, one alert, and one advisory preview
- [ ] All sample data is clearly marked as illustrative (not real company data)
- [ ] Sample data does not appear for users who have completed company profile setup
