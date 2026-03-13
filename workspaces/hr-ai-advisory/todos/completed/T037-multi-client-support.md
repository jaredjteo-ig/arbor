# T037 — Multi-Client Support — Consultant View (React + Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**React**:

- Client list page at `/clients` with table and grid view toggles
- Sortable columns: company name, sector, employees, compliance score, last activity
- Search by name/UEN, sector filter dropdown
- Summary metric cards: total clients, green/amber/red counts
- Add Client form (inline expandable) with name, UEN, sector, employee count
- Grid view with AppCard per client showing RiskTierBadge
- ClientContext for managing active client state across the app
- Client API service (`services/api/clients.ts`) with CRUD operations
- Client types added to `types/api.ts`

**Flutter**:

- ClientsScreen with search, sector ChoiceChip filter, summary metric chips
- Client cards with business icon, name, UEN, sector, employee count, compliance score, RiskTierBadge
- Floating action button to add client via bottom sheet form
- Toast confirmation on client selection

**Navigation updates**:

- Added "Emergency" and "Clients" nav items to React sidebar
- Added "Emergency" and "Clients" entries to Flutter "More" screen
- Added `/emergency`, `/emergency/:topicId`, `/clients` routes to Flutter GoRouter

## Files

- `apps/web/src/app/(dashboard)/clients/page.tsx` — React client list page
- `apps/web/src/contexts/ClientContext.tsx` — React client state context
- `apps/web/src/services/api/clients.ts` — Client API service
- `apps/web/src/types/api.ts` — Client types added
- `apps/web/src/components/shell/NavigationSidebar.tsx` — Added nav items
- `apps/mobile/lib/features/clients/screens/clients_screen.dart` — Flutter clients screen
- `apps/mobile/lib/features/settings/screens/more_screen.dart` — Added menu entries
- `apps/mobile/lib/core/routing/router.dart` — Added emergency and clients routes
