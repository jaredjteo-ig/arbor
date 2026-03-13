# T024 — Onboarding Flow (React Web)

## Status: COMPLETED

## What Was Built

### 4-Screen Onboarding Flow

1. **WelcomeStep** (`components/onboarding/WelcomeStep.tsx`)
   - Feature cards: Compliance, Calculators, Templates, Company-Specific Advice
   - Conditional CTA based on login status

2. **CompanyProfileStep** (`components/onboarding/CompanyProfileStep.tsx`)
   - Required: Company name, sector selection (10 sectors)
   - Optional collapsible sections: workforce breakdown (SC/PR/EP/SP/WP), salary range
   - "Why do we ask this?" helper on each section
   - Progressive — only name + sector required

3. **ComplianceSnapshotStep** (`components/onboarding/ComplianceSnapshotStep.tsx`)
   - Generates 3-5 instant insights based on company profile
   - DRC quota check (green/amber/red based on sector limits)
   - CPF obligations, EA coverage, TAFEP FCF, levy estimates
   - Overall compliance gauge with RiskTierBadge
   - Loading skeleton during analysis

4. **FirstQuestionStep** (`components/onboarding/FirstQuestionStep.tsx`)
   - Free-text input with voice button placeholder
   - Sector-contextual suggested questions (services, manufacturing, construction, tech, finance)
   - Generic fallback suggestions
   - Submit navigates to /advisory with question pre-filled
   - Skip option goes to dashboard

### Page (`app/(auth)/onboarding/page.tsx`)
- StepIndicator progress bar
- State management for profile data across steps
- Uses AuthContext for login detection
- Router navigation on completion

## Verification

TypeScript compiles clean (no errors).

## Files

- `apps/web/src/app/(auth)/onboarding/page.tsx`
- `apps/web/src/components/onboarding/WelcomeStep.tsx`
- `apps/web/src/components/onboarding/CompanyProfileStep.tsx`
- `apps/web/src/components/onboarding/ComplianceSnapshotStep.tsx`
- `apps/web/src/components/onboarding/FirstQuestionStep.tsx`
- `apps/web/src/components/onboarding/index.ts`
