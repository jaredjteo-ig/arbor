# T100 — Fix Confidence Display and Add Caveats

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T046, T076, T096

## What to build

Replace raw confidence percentages (e.g., "87%") with qualitative confidence indicators that are meaningful to non-technical users. Add a tooltip explaining what confidence means in this context. Ensure confidence is displayed on all response tiers including red-tier responses (currently missing). Add an automatic caveat sentence when confidence falls below 60%, prompting the user to verify with a specialist. This transforms an opaque number into actionable guidance.

## Acceptance Criteria

### Qualitative Confidence Indicator

- [ ] Replace raw percentage with a three-level qualitative label:
  - > = 75%: "High confidence"
  - 50-74%: "Moderate confidence — verify key details"
  - < 50%: "Low confidence — consult a specialist"
- [ ] Indicator uses consistent colour coding: green (high), amber (moderate), red/orange (low)
- [ ] The underlying raw percentage is available in a tooltip for users who want it (hover on the indicator)
- [ ] Tooltip also explains: "Confidence reflects how well the knowledge base matched your question"

### Confidence on All Tiers

- [ ] Red-tier responses (emergency/high-risk) show the confidence indicator
- [ ] Green-tier responses show the confidence indicator
- [ ] Amber-tier responses show the confidence indicator
- [ ] Confidence indicator position is consistent across all tiers (same layout slot)

### Automatic Caveat

- [ ] When confidence < 60%, an automatic caveat sentence is appended to the response display (not AI-generated — injected by the frontend)
- [ ] Caveat text: "Confidence is limited for this query — we recommend verifying this guidance with an employment law specialist before taking action."
- [ ] Caveat is visually distinguished from the AI response (italic, muted colour)
- [ ] Caveat does not duplicate any existing disclaimer content

## Files

- `apps/web/src/components/advisory/SystemMessage.tsx` — replace raw confidence display, add caveat logic
- `apps/web/src/components/advisory/ConfidenceIndicator.tsx` — new component (qualitative label + tooltip)

## Definition of Done

- [ ] No raw confidence percentages visible to users (percentage only in tooltip)
- [ ] Three-tier qualitative labels display correctly for all response tiers
- [ ] Confidence shown on red, amber, and green tier responses
- [ ] Automatic caveat appears when confidence < 60%
- [ ] Tooltip with raw percentage and explanation functions on hover/focus
