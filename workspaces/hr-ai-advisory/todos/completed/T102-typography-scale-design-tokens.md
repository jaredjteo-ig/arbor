# T102 — Enforce Typography Scale from Design Tokens

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: MEDIUM
**Estimated Effort**: 4h
**Dependencies**: T002, T003

## What to build

Create Tailwind utility classes mapped directly to the design token type scale (text-heading, text-subtitle, text-body-lg, text-body, text-caption, etc.). Then audit all dashboard pages to replace arbitrary Tailwind size classes (e.g., `text-2xl`, `text-sm font-medium`) with these semantic token classes. This ensures typographic consistency across the application and makes future brand updates a single-file change rather than a global search-and-replace.

## Acceptance Criteria

### Utility Classes

- [ ] Typography utility classes defined in `globals.css` mapped to design token values:
  - `.text-display` — largest heading (hero/page titles)
  - `.text-heading` — section headings
  - `.text-subtitle` — card/panel headings
  - `.text-body-lg` — lead text, important descriptions
  - `.text-body` — default body text
  - `.text-caption` — secondary labels, metadata
  - `.text-micro` — legal text, timestamps
- [ ] Classes include font-size, line-height, and font-weight as defined in tokens.json
- [ ] Classes work with Tailwind's colour utilities (e.g., `text-heading text-gray-900`)

### Audit and Replace

- [ ] All page files in `apps/web/src/app/(dashboard)/` audited
- [ ] Arbitrary Tailwind type classes replaced with token utility classes where appropriate
- [ ] No text element uses arbitrary pixel sizes (no `text-[14px]`)
- [ ] Shared component files in `apps/web/src/components/` audited and updated

### Verification

- [ ] Visual regression: all pages look identical before and after the change (diff screenshots if needed)
- [ ] No text overflow or truncation introduced by size changes
- [ ] Dark mode (if applicable) is unaffected

## Files

- `apps/web/src/app/globals.css` — define typography utility classes
- `apps/web/src/app/(dashboard)/page.tsx` — update type classes
- `apps/web/src/app/(dashboard)/advisory/page.tsx` — update type classes
- `apps/web/src/app/(dashboard)/compliance/page.tsx` — update type classes
- `apps/web/src/components/shell/NavigationSidebar.tsx` — update type classes
- `apps/web/src/components/shell/TopBar.tsx` — update type classes
- (all other page and component files found in audit)

## Definition of Done

- [ ] Typography utility classes defined in globals.css
- [ ] All dashboard pages use semantic token classes for text sizing
- [ ] No arbitrary pixel size classes in any dashboard file
- [ ] No visual regression introduced
