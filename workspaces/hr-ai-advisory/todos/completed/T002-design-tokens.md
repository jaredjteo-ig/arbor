# T002: Design system — shared tokens and i18n infrastructure — COMPLETED

**Completed**: 2026-03-11

## What was built

### Design Tokens (single source of truth)

- `design-tokens/tokens.json` — canonical token specification with all colors, typography, spacing, radius, shadows, touch targets
- `design-tokens/generate.py` — generator script that produces both React and Flutter files from tokens.json
- Colors: primary navy (#1E3A5F), secondary teal (#0D6E4F), risk tiers (green/amber/red), authority badges (statutory/guideline/best-practice), semantic, surface colors
- Typography: Source Sans 3, 10-level scale from 11px overline to 28px page title, 16px body minimum
- Text size accessibility: Normal (1x) / Large (1.15x) / Extra Large (1.3x) multipliers built into the token system
- Spacing: 4px base unit, xs through 3xl scale
- Border radius: sm(6px) through full(9999px)
- Shadows: card, raised, modal
- Touch targets: 48px minimum

### React (apps/web/)

- `src/lib/tokens.ts` — auto-generated TypeScript constants for all tokens
- `src/app/globals.css` — CSS custom properties with Tailwind CSS v4 integration, text size scaling via data attributes
- `src/app/layout.tsx` — Source Sans 3 font loaded via next/font
- Focus indicators: 2px solid primary outline for WCAG AAA

### Flutter (apps/mobile/)

- `lib/core/design/tokens/tokens.dart` — auto-generated Dart constants (AppColors, AppTypography, AppSpacing, AppRadius, AppTouch, TextSizePreference enum)
- `lib/core/design/tokens/app_theme.dart` — Material 3 ThemeData that uses tokens, supports text size multiplier
- Flutter theme covers: colorScheme, textTheme, elevatedButton, outlinedButton, inputDecoration, card, bottomNavigationBar

### i18n Infrastructure

- React: i18next configured with `src/lib/i18n/en.json` (app, nav, auth, common, risk, authority, feedback, accessibility strings)
- Flutter: ARB files at `lib/l10n/app_en.arb` with matching string keys, `l10n.yaml` configured, `generate: true` in pubspec
- Singapore date formatting ("15 Mar 2026") and currency ("S$") standardized

## Verification

- 22/22 pytest tests passing (test_design_tokens.py)
- Next.js builds successfully with new theme
- Flutter analysis: no issues found
- Token generator produces consistent output for both platforms
