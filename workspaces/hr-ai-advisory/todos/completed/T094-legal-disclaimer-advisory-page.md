# T094 — Add Legal Disclaimer to Advisory Page

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 2h
**Dependencies**: T026, T046

## What to build

Add a persistent, non-dismissible disclaimer footer to the /advisory page that matches the disclaimer already shown in the side panel. Also correct the misleading copy in the empty state from "instant, cited answers" to "instant, cited guidance" (answers implies certainty; guidance is legally safer). Add an AI disclosure badge to every system message so users always know they are reading AI-generated content.

## Acceptance Criteria

### Persistent Disclaimer Footer

- [ ] A non-dismissible disclaimer footer is visible at the bottom of the /advisory chat area at all times
- [ ] Footer text is consistent with the side panel disclaimer (same wording, not a paraphrase)
- [ ] Footer does not scroll away with chat messages — it is fixed at the bottom of the viewport or the chat container
- [ ] Footer uses the muted/secondary text colour from design tokens and does not visually compete with the chat

### Copy Fix

- [ ] Empty state headline or subtext changes from "instant, cited answers" to "instant, cited guidance"
- [ ] Any other occurrences of "instant answers" in the advisory page copy are reviewed and updated accordingly

### AI Disclosure Badge

- [ ] Every system message (AI-generated response) shows a small "AI-generated" or "AITE Advisory" badge
- [ ] Badge is visually distinct but not distracting — a subtle label consistent with the design system
- [ ] User messages do not show the badge

## Files

- `apps/web/src/components/advisory/ChatContainer.tsx` — add persistent disclaimer footer
- `apps/web/src/components/advisory/SystemMessage.tsx` — add AI disclosure badge to message header
- `apps/web/src/app/(dashboard)/advisory/page.tsx` — fix empty state copy

## Definition of Done

- [ ] Disclaimer footer visible on /advisory at all times, cannot be closed
- [ ] "Instant, cited guidance" used throughout advisory page copy
- [ ] AI disclosure badge appears on every system message
- [ ] Disclaimer wording matches side panel disclaimer exactly
