# T053 — HRIS Integration API Adapters

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Provider Taxonomy**:

- `HrisProvider` enum (TALENOX, PAYBOY, SWINGVY, CSV)
- `SyncFrequency` enum for scheduling sync intervals
- `SyncStatus` enum for tracking sync operation state

**Data Models**:

- `HrisSyncConfig` dataclass for provider connection configuration — provider, credentials, sync frequency, field mappings
- `EmployeeRecord` normalised dataclass — unified employee representation across all providers with standardised nationality, employment type, and pass type fields
- `HrisSyncResult` dataclass with sync metadata — status, records synced/failed, error details, timestamp

**Provider Adapters**:

- `_sync_talenox()` — async adapter for Talenox API with employee data normalisation
- `_sync_payboy()` — async adapter for Payboy API with employee data normalisation
- `_sync_swingvy()` — async adapter for Swingvy API with employee data normalisation
- All three are production placeholders with proper async signatures and error handling

**Public API**:

- `sync_from_provider()` — async sync operation that dispatches to the correct provider adapter with comprehensive error handling and result tracking
- `import_csv()` — CSV import using DictReader with field normalisation to EmployeeRecord format
- `get_sync_history()` — retrieves sync audit trail for a company

**Normalisation Helpers**:

- Nationality normalisation (e.g., "Singaporean" / "SC" to standardised values)
- Employment type normalisation (full-time, part-time, contract variants)
- Pass type normalisation (EP, S Pass, WP, DP variants)

## Files

- `src/hr_advisory/integrations/hris_adapters.py` — HRIS integration adapters module
- `src/hr_advisory/integrations/__init__.py` — package init
