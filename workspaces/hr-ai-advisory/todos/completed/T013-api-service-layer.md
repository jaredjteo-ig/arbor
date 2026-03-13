# T013 — API Service Layer (React + Flutter)

## Status: COMPLETED

## What Was Built

### React (TanStack Query)

| Layer | Files | Purpose |
| --- | --- | --- |
| Base client | client.ts, sse.ts | Auto-auth headers, 401 refresh+retry, SSE streaming via fetch+ReadableStream |
| Service modules | 8 files (advisory, calculators, compliance, documents, profile, kb, search, alerts) | Typed API calls using base client |
| TanStack hooks | 8 files matching services | useQuery/useMutation with query key factories, cache invalidation, conditional fetching |
| Types | api.ts | All request/response TypeScript interfaces |
| Provider | Providers.tsx updated | QueryClientProvider with 1-min staleTime, single retry |

### Flutter (Dio + Riverpod)

| Layer | Files | Purpose |
| --- | --- | --- |
| Network | api_client.dart, sse_client.dart, api_error.dart | Configured Dio with auth interceptor, SSE parser, structured errors |
| Models | 7 domain files + barrel | Immutable data classes with fromJson/toJson |
| Repositories | 7 domain files + barrel | Typed API methods, DioException → ApiError conversion |
| Providers | api_providers.dart | Repository providers + AsyncNotifier family providers for cached data |

## Verification

- React: `next build` passes — 16 routes, zero TypeScript errors
- Flutter: `flutter analyze` — no issues found
- Backend: 33 auth + 27 Nexus API tests still passing
