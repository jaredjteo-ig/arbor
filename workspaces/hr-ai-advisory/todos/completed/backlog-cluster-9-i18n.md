# Backlog Cluster 9 — B17 Minimum-Viable i18n

**Status:** Shipped (scaffold + 2 translated surfaces)
**Date:** 2026-04-28

## What shipped

A working translation layer in `apps/web` covering English plus three
Singapore-relevant locales: Mandarin (Simplified), Bahasa Melayu, and
Tamil. A user can flip languages from Settings and the dashboard
navbar plus the My Payslips page render in their chosen language
immediately, with the choice persisted to `localStorage` so it
survives reloads.

## Approach

The Next.js app already had `i18next` + `react-i18next` +
`i18next-browser-languagedetector` installed and an `en.json` bundle
under `apps/web/src/lib/i18n/`. The scaffold was wired up via a
side-effect import in `Providers.tsx` but was effectively dormant —
only a handful of auth pages used `t()` and there was a single locale
file.

Rather than swap libraries, we finished the wiring:

1. Expanded `en.json` to cover the navbar, topbar, settings page,
   language switcher, and My Payslips strings.
2. Authored three new bundles — `zh-CN.json`, `ms-MY.json`,
   `ta-SG.json` — by hand using Singapore HR vocabulary (CPF, SDL,
   FWL, SHG kept as established acronyms; full statutory names
   localised; "Tripartite Guideline" rendered idiomatically per
   locale).
3. Updated `lib/i18n/index.ts` to register all four bundles, declare
   `SUPPORTED_LOCALES` / `DEFAULT_LOCALE`, expose `setLocale()` and
   `getLocale()` helpers, and configure `LanguageDetector` to read
   from `localStorage` first (`arbor-locale` key) then browser
   language. `setLocale()` also mirrors the choice onto
   `<html lang>` for screen readers and CSS `:lang()` selectors.
4. Built a `LocaleSwitcher` component
   (`apps/web/src/components/shell/LocaleSwitcher.tsx`) — a
   four-card radio group with native-script labels, hydration-safe
   so it does not flash on initial render, accessible via
   `role="radiogroup"` / `aria-checked`.
5. Replaced the "More languages coming soon" `AlertBanner` in
   Settings with the live `LocaleSwitcher`.
6. Switched the navbar and topbar to consume `t()`. The sidebar
   already carried `labelKey` strings on every nav item, so the
   change was a one-line per renderer using
   `t(item.labelKey, { defaultValue: item.label })` — this means
   that any future locale that misses a key falls back to the
   English default rather than printing `nav.dashboard` to the user.
7. Translated the `My Payslips` page end-to-end (page heading,
   refresh, status badges, earnings/deductions/employer
   contributions/statutory rows, expanded detail labels, error and
   empty states, download PDF button).
8. Added a Python regression test
   (`tests/regression/test_b17_i18n_locale_coverage.py`) that loads
   each locale JSON, parametrises across 23 user-visible keys and 4
   locales (97 cases total), and additionally spot-checks that
   non-English locales actually translate `nav.dashboard`,
   `nav.settings`, and `nav.my-payslips` rather than echoing the
   English copy.

## Translated surfaces (proof of concept)

| Surface                                        | Status                                                                                          |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `NavigationSidebar` (admin nav)                | Translated                                                                                      |
| `NavigationSidebar` (employee nav)             | Translated                                                                                      |
| `TopBar` (search, notifications, profile menu) | Translated                                                                                      |
| `Settings → Language` card                     | Translated (live switcher)                                                                      |
| `My Payslips` page                             | Translated (full page)                                                                          |
| Auth pages (login/signup/forgot/reset)         | Already used `t()`; English-only string table previously, now multilingual via expanded bundles |

## Still in English (future work — straightforward to extend)

The scaffold is the load-bearing piece; rolling translations across
the rest of the app is a mechanical pass per page. The remaining
surfaces all use literal strings today:

- Admin pages: Dashboard, Advisory, Compliance, Calculators,
  Documents, Payroll runs / reports / filings, Leave, Policies,
  Claims, Attendance, Shifts, Employees, Onboarding (admin),
  Appraisals, Projects, Inventory, Recruitment (4 tabs +
  settings), Approvals, Reports, Analytics, Emergency, Training,
  Admin, Integrations, Help.
- Employee pages: My Dashboard, My Onboarding, My Profile,
  My Leave, My Claims, My Attendance, My Timesheets, My Inventory,
  Advisory.
- Cross-cutting components: ShadowAgent / ArborHistory /
  CommandSurface, AdvisoryPanel, ToastMessages from API
  responses, server-generated email and PDF copy.
- Date / number formatting still uses `en-SG` literals — once
  more locales need date formatting, replace `toLocaleDateString`
  call sites with the active locale.
- The two existing `(auth)` pages already call `useTranslation()`
  and reference keys that exist in all four bundles, so they will
  pick up the new translations on next render — no further code
  change needed there.

## Validation

- New regression test: 97/97 passing
  (`.venv/bin/pytest tests/regression/test_b17_i18n_locale_coverage.py -v`).
- Did not re-run the full unit suite (test-once protocol).
- Did not touch backend code, the active todo file, or
  `.test-results`.

## Files

### New

- `apps/web/src/lib/i18n/zh-CN.json`
- `apps/web/src/lib/i18n/ms-MY.json`
- `apps/web/src/lib/i18n/ta-SG.json`
- `apps/web/src/components/shell/LocaleSwitcher.tsx`
- `tests/regression/test_b17_i18n_locale_coverage.py`

### Modified

- `apps/web/src/lib/i18n/en.json` (expanded key coverage)
- `apps/web/src/lib/i18n/index.ts` (multi-locale init, helpers)
- `apps/web/src/components/shell/NavigationSidebar.tsx`
- `apps/web/src/components/shell/TopBar.tsx`
- `apps/web/src/app/(dashboard)/settings/page.tsx`
- `apps/web/src/app/(dashboard)/my-payslips/page.tsx`
- `apps/web/src/app/(dashboard)/layout.tsx` (sets `<html lang>`)
