# T055 — Offline Capabilities (Flutter)

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Cache Management**:

- `OfflineManager` — manages local caching of API responses and advisory data for offline access, with connectivity detection and automatic cache invalidation

**Connectivity Detection**:

- Monitors network state transitions (online/offline) and triggers appropriate UI updates and sync behaviour

**Offline UI**:

- `OfflineBanner` — visual indicator widget that appears when the app detects offline mode, informing users that cached data is being used

**Sync Queue**:

- `SyncQueue` — queues write operations (feedback submissions, calculator inputs, etc.) performed while offline and replays them in order when connectivity is restored

## Files

- `apps/mobile/lib/core/offline/offline_manager.dart` — cache management and connectivity detection
- `apps/mobile/lib/core/offline/offline_banner.dart` — offline mode indicator banner widget
- `apps/mobile/lib/core/offline/sync_queue.dart` — operation queuing for offline writes
