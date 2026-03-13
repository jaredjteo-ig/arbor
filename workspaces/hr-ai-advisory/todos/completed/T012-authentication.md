# T012 — Authentication and Authorization

## Status: COMPLETED

## What Was Built

### Backend Auth Service
- **AuthService** — Pure service layer: bcrypt password hashing, PyJWT token creation/validation, DataFlow user CRUD
- **Auth Middleware** — `get_current_user` (JWT extraction from Bearer header), `require_role` (role-based access factory)
- **Auth Router** — 7 real endpoints replacing placeholders: register, login, refresh, me, logout, password-reset-request, password-reset
- Proper HTTP status codes: 200, 400, 401, 403, 409
- Security: no password/token logging, email enumeration prevention on reset

### React Frontend
- **AuthContext** — Token storage in localStorage, auto-refresh on mount, login/register/logout
- **ProtectedRoute** — Auth guard with optional role requirement
- **Auth pages** — Login, signup, forgot-password, reset-password (centered card layout, no sidebar)
- **(dashboard) route group** — All authenticated routes wrapped in ProtectedRoute + AppShell
- **API client** — auth.ts with typed methods for all auth endpoints
- **i18n** — 33 auth translation keys in en.json

### Flutter Frontend
- **AuthService** — Dio HTTP client + FlutterSecureStorage token persistence
- **AuthState** — Sealed class hierarchy (Initial/Loading/Authenticated/Unauthenticated/Error)
- **AuthNotifier** — Riverpod 3 Notifier with checkAuth, login, register, logout
- **Auth screens** — Login, signup, forgot-password, reset-password (navy background, white card)
- **AuthInterceptor** — Dio interceptor: auto-attach tokens, transparent refresh on 401
- **Router** — Auth routes outside app shell, derived `isAuthenticatedProvider` for guard compatibility
- **ARB** — 30+ localized auth strings

## Verification

- Backend: 33 tests passed + 27 existing Nexus API tests still passing (60 total)
- React: `next build` succeeds with zero errors, all 16 routes generated
- Flutter: `flutter analyze` — no issues found
