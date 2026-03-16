# T103 — Fix Accessibility Issues

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: HIGH
**Estimated Effort**: 4h
**Dependencies**: T003, T036

## What to build

Address three identified accessibility failures: (1) body text using gray-400 which fails WCAG AA contrast ratio, (2) emergency page interactive cards implemented as div elements with role="button" rather than native button or link elements, and (3) the profile dropdown lacking keyboard navigation (arrow keys, Escape). These are not cosmetic — they prevent keyboard-only users and screen reader users from using the product.

## Acceptance Criteria

### Contrast Fix (WCAG AA)

- [ ] All body text colours are gray-500 minimum (4.5:1 contrast ratio on white background)
- [ ] Any uses of `text-gray-400` for body or label text replaced with `text-gray-500` or darker
- [ ] Placeholder text in inputs may remain gray-400 (this is acceptable per WCAG)
- [ ] Secondary/caption text that must remain lighter is reviewed and documented with contrast ratio
- [ ] Run axe-core or equivalent contrast check on all updated pages — no WCAG AA failures

### Emergency Card Fix

- [ ] Emergency page playbook/action cards converted from `div[role="button"]` to native `<button>` or `<a>` elements
- [ ] All interactive behaviour (click, hover, focus) preserved
- [ ] Cards focus correctly with Tab key and show visible focus ring
- [ ] Screen reader announces interactive cards correctly ("button" or link role)

### Profile Dropdown Keyboard Navigation

- [ ] Profile dropdown opens via Enter or Space key when trigger is focused
- [ ] Arrow keys (Up/Down) navigate between dropdown menu items
- [ ] Escape key closes the dropdown and returns focus to the trigger
- [ ] Tab key closes the dropdown if focus leaves it
- [ ] Dropdown items are native `<button>` or `<a>` elements (not divs)

### Verification

- [ ] Manual keyboard-only test: navigate to profile dropdown, open it, navigate items, close with Escape
- [ ] Manual keyboard-only test: navigate to emergency page, Tab to action cards, activate with Enter
- [ ] Run automated accessibility scan (axe-core) on auth pages, dashboard, advisory, emergency pages — no critical violations

## Files

- `apps/web/src/app/globals.css` — update default text colour variables
- `apps/web/src/components/shell/TopBar.tsx` — fix profile dropdown keyboard navigation
- `apps/web/src/app/(dashboard)/emergency/page.tsx` — convert div[role="button"] to native elements
- Any other files found during the gray-400 audit

## Definition of Done

- [ ] No body text using gray-400 or lighter
- [ ] Emergency cards are native button/link elements with keyboard support
- [ ] Profile dropdown fully keyboard navigable (arrows, Escape, Tab)
- [ ] Automated axe-core scan reports no critical accessibility violations on audited pages
