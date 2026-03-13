# T006 — App Shell and Navigation (Flutter)

## Status: COMPLETED

## What Was Built

### Core Infrastructure
- **GoRouter** (`lib/core/routing/router.dart`) — Full route configuration with StatefulShellRoute.indexedStack for bottom nav state preservation. Auth/onboarding redirect guards. All application routes registered.
- **AppShell** (`lib/core/shell/app_shell.dart`) — Material 3 NavigationBar with 5 tabs: Home, Advisory, Tools, Docs, More. 72dp height, primaryNavy selected color, 48dp touch targets.
- **Auth providers** (`lib/core/providers/auth_providers.dart`) — Riverpod 3 Notifier pattern for isAuthenticated and isOnboarded state.
- **Lifecycle observer** (`lib/core/lifecycle/app_lifecycle_observer.dart`) — WidgetsBindingObserver logging lifecycle transitions, extensible for token refresh.

### Route Structure
| Route | Screen | Location |
|-------|--------|----------|
| `/` | Dashboard | Inside shell (Home tab) |
| `/advisory` | Advisory chat | Inside shell (Advisory tab) |
| `/calculators` | Calculators list | Inside shell (Tools tab) |
| `/calculators/:type` | Calculator detail | Inside shell |
| `/documents` | Documents | Inside shell (Docs tab) |
| `/compliance` | Compliance dashboard | Over shell (from More) |
| `/compliance/:category` | Category detail | Over shell |
| `/alerts` | Alerts | Over shell (from More) |
| `/profile` | Company profile | Over shell (from More) |
| `/settings` | Settings | Over shell (from More) |
| `/help` | Help | Over shell (from More) |
| `/auth/login` | Login | Outside shell |
| `/auth/signup` | Signup | Outside shell |
| `/onboarding` | Onboarding | Outside shell |

### Files Created
- 18 new files (core infrastructure + 14 placeholder screens)
- 2 files updated (main.dart, widget_test.dart)

## Architecture Decisions
- Riverpod 3 Notifier pattern (not legacy StateProvider)
- StatefulShellRoute.indexedStack preserves tab navigation stacks independently
- "More" menu routes push over the shell with back button
- Auth/onboarding routes sit outside the shell entirely
- All screens use EmptyState design system component with contextual icons

## Verification
- `flutter analyze --no-fatal-infos` — No issues found
- `flutter test` — Passes (verifies all 5 nav tabs and Dashboard render)
