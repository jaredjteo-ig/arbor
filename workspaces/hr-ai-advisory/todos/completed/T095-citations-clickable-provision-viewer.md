# T095 — Make Citations Clickable with Provision Viewer

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 6h
**Dependencies**: T045, T064, T081

## What to build

Each SourceCitation pill in an advisory response must be clickable and must open a modal or side panel that shows: (1) the full provision text from the knowledge base, and (2) a link to the official government source (e.g., MOM website, CPF Board). Currently the onClick handler on SourceCitation is never passed a real handler — citations are inert decorations. Making them interactive is the single most important step toward verifiability and user trust.

## Acceptance Criteria

### Clickable Citations

- [ ] Every SourceCitation pill has an onClick handler that opens the ProvisionViewer
- [ ] Citation pills have a visual affordance indicating they are interactive (cursor: pointer, subtle underline or chevron icon)
- [ ] Clicking a citation does not navigate away from the advisory page

### ProvisionViewer Component

- [ ] New component `ProvisionViewer` (modal or side panel) created
- [ ] Displays: provision title, full provision text as retrieved from the KB, authority level badge, domain label
- [ ] Displays a "View official source" link that opens the government URL in a new tab
- [ ] Government source URL is stored in the KB provision record (add field if missing)
- [ ] ProvisionViewer is dismissible via close button, Escape key, or clicking outside
- [ ] If the full provision text cannot be retrieved, shows a graceful fallback with the citation summary

### Backend / API

- [ ] API can return full provision text by provision ID or citation reference
- [ ] Provision records include an `official_source_url` field (add migration if missing)
- [ ] Existing provision records backfilled with official source URLs where known

## Files

- `apps/web/src/components/design-system/SourceCitation.tsx` — add onClick prop, visual affordance
- `apps/web/src/components/advisory/SystemMessage.tsx` — pass onClick handler to each SourceCitation
- `apps/web/src/components/advisory/ProvisionViewer.tsx` — new component (modal/side panel)
- `src/hr_advisory/models/knowledge_base.py` — add `official_source_url` field to provision model
- `src/hr_advisory/api/routers/advisory.py` — add endpoint or augment existing to return full provision text

## Definition of Done

- [ ] Clicking any citation pill opens ProvisionViewer with full provision text
- [ ] "View official source" link present and opens correct government URL in new tab
- [ ] ProvisionViewer dismisses correctly via all three methods (button, Escape, outside click)
- [ ] Fallback shown gracefully when provision text unavailable
- [ ] All existing citation pills in the design system remain visually unchanged (only behaviour added)
