"""HRIS integration adapters (T053).

Provides read-only data sync from third-party HRIS platforms and CSV import.
"""

from hr_advisory.integrations.hris_adapters import (
    HrisProvider,
    HrisSyncConfig,
    HrisSyncResult,
    EmployeeRecord,
    sync_from_provider,
    import_csv,
    get_sync_history,
)

__all__ = [
    "HrisProvider",
    "HrisSyncConfig",
    "HrisSyncResult",
    "EmployeeRecord",
    "sync_from_provider",
    "import_csv",
    "get_sync_history",
]
