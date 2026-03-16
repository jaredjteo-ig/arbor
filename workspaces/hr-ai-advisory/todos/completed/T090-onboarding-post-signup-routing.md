# T090 — Wire Onboarding Flow to Post-Signup

**Status**: ACTIVE
**Milestone**: 10 — Demo-Ready First Impressions
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T024, T089

## What to build

After a user registers, they should be routed directly to /onboarding instead of /. Persist an onboarding completion flag in user state so the system knows whether setup was completed. If onboarding is incomplete, show a resume banner on the dashboard. Fix the "Set Up Company Profile" call-to-action button so it routes to /onboarding (not /profile or /settings) for users who have not completed it. This closes the gap where first-time users land on an empty dashboard with no guided path forward.

## Acceptance Criteria

### Post-Signup Routing

- [ ] After successful registration, redirect to /onboarding (not /)
- [ ] Onboarding completion state is persisted (database field or localStorage with server sync)
- [ ] Already-onboarded users who revisit /onboarding are redirected to /

### Resume Banner

- [ ] If onboarding is not complete, a non-intrusive banner appears at the top of the dashboard
- [ ] Banner text: "Complete your company profile to unlock your compliance score" with a "Continue setup" button
- [ ] Banner is dismissible for the session but reappears on next login if still incomplete
- [ ] Banner does not appear once onboarding is marked complete

### CTA Button Fix

- [ ] "Set Up Company Profile" button on the dashboard empty state routes to /onboarding
- [ ] If the user has already completed onboarding (has a company profile), the button routes to /settings/company instead
- [ ] No hard-coded /profile routes remain in the dashboard for this CTA

## Files

- `apps/web/src/contexts/AuthContext.tsx` — add onboarding_complete field, expose it via context
- `apps/web/src/app/(auth)/signup/page.tsx` — change post-registration redirect to /onboarding
- `apps/web/src/app/(dashboard)/page.tsx` — add resume banner, fix CTA button routing
- `apps/web/src/components/dashboard/OnboardingResumeBanner.tsx` — new component

## Definition of Done

- [ ] New user flow: register → /onboarding (not /)
- [ ] Returning user with incomplete onboarding sees resume banner on dashboard
- [ ] Returning user with complete onboarding sees no banner
- [ ] CTA button routing is correct based on profile completion state
