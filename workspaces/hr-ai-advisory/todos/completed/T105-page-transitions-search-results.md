# T105 — Add Page Transitions and Search Results

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: LOW
**Estimated Effort**: 5h
**Dependencies**: T005, T093

## What to build

Add subtle fade-in route transition animations so navigation between pages feels polished rather than abrupt. Implement a real-time search results dropdown in the top bar search input: as the user types, show matching results from the knowledge base, advisory history, and calculator shortcuts. This is the standard UX pattern for enterprise applications and elevates the overall quality impression significantly.

## Acceptance Criteria

### Page Transitions

- [ ] Route changes produce a subtle fade-in animation (opacity 0 to 1, ~150ms)
- [ ] No layout shift during the transition
- [ ] Transition does not add perceived latency (should feel instantaneous but polished)
- [ ] Transition works in both directions (navigating forward and back)
- [ ] Implementation uses CSS or Framer Motion (not a heavy library); check if Framer Motion is already in dependencies before adding

### Search Results Dropdown

- [ ] Top bar search input shows a dropdown as the user types (after 2+ characters)
- [ ] Dropdown shows results in up to 3 sections:
  - "Knowledge Base" — matching regulatory provisions/articles (search against KB API)
  - "Advisory History" — past conversations matching the query
  - "Quick Actions" — calculators or pages matching the query text
- [ ] Each section shows at most 3 results; "See all" link at section bottom if more exist
- [ ] Selecting a KB result navigates to a provision viewer or advisory pre-filled with that topic
- [ ] Selecting an advisory history result opens that conversation
- [ ] Selecting a quick action navigates to the relevant page/calculator
- [ ] Dropdown closes on Escape, on outside click, or after selection
- [ ] Keyboard navigation: arrow keys move between results, Enter selects

### SearchResults Component

- [ ] New `SearchResults` component extracted for the dropdown UI
- [ ] Handles loading state (skeleton items while fetching)
- [ ] Handles empty state: "No results for [query]" with a "Search knowledge base" fallback link
- [ ] Debounced fetch (300ms) to avoid excessive API calls

## Files

- `apps/web/src/app/layout.tsx` — add page transition wrapper
- `apps/web/src/components/shell/TopBar.tsx` — wire search input to SearchResults
- `apps/web/src/components/shell/SearchResults.tsx` — new component

## Definition of Done

- [ ] Route changes produce a fade-in animation
- [ ] Search input shows results dropdown after 2 characters
- [ ] All three result sections (KB, history, quick actions) populate correctly
- [ ] Keyboard navigation through results works
- [ ] Dropdown closes correctly on all dismissal triggers
