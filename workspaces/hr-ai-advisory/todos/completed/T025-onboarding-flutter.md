# T025 — Onboarding Flow (Flutter Mobile)

## Status: COMPLETED

## What Was Built

### 4-Screen Onboarding Flow (Flutter)

Full-screen PageView-based onboarding matching the React web version:

1. **WelcomeStep** — Feature cards (Compliance, Calculators, Templates, Company-Specific), "Get Started" CTA
2. **CompanyProfileStep** — Company name, sector dropdown (10 sectors), collapsible workforce breakdown (SC/PR/EP/SP/WP), collapsible salary range, "Why do we ask this?" helpers
3. **ComplianceSnapshotStep** — Deterministic insight generation matching React logic (DRC quota, CPF, EA coverage, TAFEP FCF, levy estimates), RiskTierBadge with overall compliance gauge, 1.2s simulated analysis
4. **FirstQuestionStep** — Free-text input with voice button, sector-specific suggested questions, haptic feedback on send, skip option

### Key Implementation Details

- `OnboardingProfileData` class for cross-step state
- `PageController` with physics disabled (no swipe between steps)
- Uses `RiskTier` enum from design system (not strings)
- Uses `AppRadius` tokens directly (BorderRadius type, not double)
- Calls `ref.read(isOnboardedProvider.notifier).set(true)` on completion
- GoRouter already configured for `/onboarding` route with redirect guards

## Verification

`flutter analyze` — 0 issues found.

## Files

- `apps/mobile/lib/features/onboarding/screens/onboarding_screen.dart` (replaced placeholder)
