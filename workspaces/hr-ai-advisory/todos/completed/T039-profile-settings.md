# T039 — Company Profile and User Settings (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**React — Company Profile** (629 lines):

- Card-based layout with company details, workforce, and contact sections
- Edit mode per section (not a giant form)
- Profile completeness indicator with percentage
- Warning AlertBanner when profile changes affect compliance
- Profile change history

**React — User Settings** (551 lines):

- Text size preference (Normal/Large/Extra Large) radio selection
- Notification preferences: email, push, in-app toggles + frequency
- Language selection (English, more coming)
- Data & Privacy: Export My Data (PDPA), Delete Account with confirmation dialog

**Flutter — Company Profile**:

- ProfileScreen with section-based editing (details, workforce, contact)
- Circular completeness indicator
- Per-section edit/save/cancel flow
- Profile change history list

**Flutter — User Settings**:

- SettingsScreen with text size radio options, notification SwitchListTiles
- Alert frequency ChoiceChips (Immediately/Daily/Weekly)
- Language selection with "coming soon" note
- Data & Privacy section with Export and Delete Account flows
- PDPA compliance information display

## Files

- `apps/web/src/app/(dashboard)/profile/page.tsx` — React profile
- `apps/web/src/app/(dashboard)/settings/page.tsx` — React settings
- `apps/mobile/lib/features/profile/screens/profile_screen.dart` — Flutter profile
- `apps/mobile/lib/features/settings/screens/settings_screen.dart` — Flutter settings
