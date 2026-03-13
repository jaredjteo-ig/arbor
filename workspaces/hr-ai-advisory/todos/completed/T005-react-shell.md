# T005 — App Shell and Navigation (React)

## Status: COMPLETED

## What Was Built

### Shell Components (`src/components/shell/`)
- **NavigationSidebar** — Persistent left sidebar with primary nav (Dashboard, Advisory, Calculators, Documents, Compliance) and secondary nav (Alerts, Company Profile, Settings, Help). Expanded (240px with labels) and collapsed (60px icon-only with tooltips) modes. Active route highlighting via usePathname.
- **TopBar** — Fixed 56px top bar with hamburger toggle (mobile), expandable search, notification bell with badge, profile avatar with dropdown (Profile, Settings, Log out).
- **AppShell** — Layout wrapper composing sidebar + topbar + content. Responsive: hidden sidebar on mobile (<768px, toggleable with overlay), collapsed on tablet (768-1024px), expanded on desktop (>=1024px). State persisted in localStorage.

### Route Pages (Next.js App Router)
11 pages created with placeholder content:
- `/` — Dashboard
- `/advisory` — Advisory chat
- `/calculators` — Calculators index
- `/calculators/[type]` — Dynamic calculator detail
- `/documents` — Documents
- `/compliance` — Compliance dashboard
- `/compliance/[category]` — Dynamic compliance category
- `/alerts` — Alerts
- `/profile` — Company Profile
- `/settings` — Settings
- `/help` — Help

### Error Handling
- `error.tsx` — Error boundary using ErrorState component with retry
- `not-found.tsx` — Custom 404 using EmptyState with "Go to Dashboard" link

## Design Decisions
- Next.js 16 App Router (not React Router) — file-based routing
- Dynamic routes use `params: Promise<{...}>` with await (Next.js 16 convention)
- SSR hydration skeleton to prevent layout shift
- Body scroll locked when mobile overlay is open
- All colors via CSS custom properties, 44px min touch targets

## Verification
- `npx next build` — compiles cleanly, all 12 routes registered
