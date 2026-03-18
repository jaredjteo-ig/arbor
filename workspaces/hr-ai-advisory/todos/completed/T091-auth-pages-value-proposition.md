# T091 — Split-Screen Auth Pages with Value Proposition

**Status**: ACTIVE
**Milestone**: 10 — Demo-Ready First Impressions
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T012

## What to build

Add a left panel to the login and signup pages that communicates what Arbor is and why a user should sign up. Currently the auth pages are bare white cards that say nothing about the product. A visitor arriving from any source sees no value signal before they decide whether to create an account. The left panel must include a product tagline, 3-4 feature highlights with icons, and trust signals (e.g., "MOM-aligned", "PDPA-compliant", "Trusted by 200+ Singapore SMEs").

## Acceptance Criteria

### Layout

- [ ] Auth pages use a two-column layout on desktop: left panel (value proposition) and right panel (form)
- [ ] On mobile, the left panel collapses and only the form is shown (full-width)
- [ ] The layout is handled in the auth layout file so it applies to both login and signup consistently

### Left Panel Content

- [ ] Product tagline displayed prominently: "AI-Powered HR Compliance for Singapore"
- [ ] 3-4 feature highlights with icons, e.g.:
  - "Instant answers citing Employment Act, CPF, and MOM regulations"
  - "Compliance health score for your company"
  - "Generate employment contracts and HR letters in seconds"
  - "Emergency escalation to employment law specialists"
- [ ] Trust signals section: MOM-aligned guidance, PDPA-compliant, secure infrastructure
- [ ] Arbor logo and branding in left panel

### Visual Quality

- [ ] Left panel uses brand gradient or primary colour background with white text
- [ ] Icons from the existing icon library (no new dependencies)
- [ ] Design token typography and spacing applied consistently

## Files

- `apps/web/src/app/(auth)/layout.tsx` — restructure to two-column split layout
- `apps/web/src/app/(auth)/login/page.tsx` — verify form panel renders correctly in new layout
- `apps/web/src/app/(auth)/signup/page.tsx` — verify form panel renders correctly in new layout
- `apps/web/src/components/auth/ValuePropositionPanel.tsx` — new left panel component

## Definition of Done

- [ ] Login page shows two-column layout on desktop with value proposition on the left
- [ ] Signup page shows two-column layout on desktop with value proposition on the left
- [ ] Mobile layout is single-column (form only)
- [ ] All content is accurate and uses the design token system
