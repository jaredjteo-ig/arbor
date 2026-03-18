# T089 — Fix Broken Greeting and Dashboard Empty State

**Status**: ACTIVE
**Milestone**: 10 — Demo-Ready First Impressions
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T029

## What to build

Fix the "Welcome, there" greeting where the user's name fails to resolve. Then redesign the dashboard experience for users who have not yet created a company profile. The current empty-state is a white void that communicates nothing. Replace it with an onboarding progress tracker, a value preview (sample compliance score, sample advisory Q&A snippet), and contextual guidance cards. The dashboard must demonstrate what Arbor can do, not demand setup before showing any value.

## Acceptance Criteria

### Greeting Fix

- [ ] Resolve user first name from auth context and display "Welcome, [First Name]"
- [ ] Fallback gracefully to "Welcome back" if name is not available (no trailing comma-space)
- [ ] Name is sourced from the authenticated user profile, not hardcoded

### Empty State Redesign

- [ ] Remove the blank white card that appears when no company profile exists
- [ ] Add onboarding progress tracker showing setup steps (e.g., Create Profile, Add Employees, Ask Your First Question) with completion state per step
- [ ] Add a "Value Preview" section with:
  - Sample compliance score card (clearly labelled "Example — set up your profile to see your score")
  - Sample advisory Q&A snippet showing a realistic question and structured answer
- [ ] Add contextual guidance cards with specific call-to-action buttons ("Set up your company profile", "Try asking a question")
- [ ] The empty state must visually communicate platform capabilities, not just a setup prompt

### Visual Quality

- [ ] Empty state uses the existing design token colour palette and component library
- [ ] Mobile-responsive layout maintained
- [ ] No layout shift or flash when auth context resolves

## Files

- `apps/web/src/app/(dashboard)/page.tsx` — main dashboard page
- `apps/web/src/components/dashboard/OnboardingProgressTracker.tsx` — new component
- `apps/web/src/components/dashboard/ValuePreview.tsx` — new component
- `apps/web/src/contexts/AuthContext.tsx` — verify user name is available on context

## Definition of Done

- [ ] Greeting shows resolved first name on all pages that display it
- [ ] New user dashboard shows progress tracker, value preview, and guidance cards
- [ ] Existing (returning) user dashboard is unaffected
- [ ] No console errors related to undefined user properties
