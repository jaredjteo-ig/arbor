"""HRIS Integration Adapters (T053).

Read-only data sync from third-party HRIS platforms to auto-populate
company profiles. Supports multiple providers via API and generic CSV import.

All integrations are read-only (we don't write back to source HRIS).
OAuth-based authentication for API integrations.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class HrisProvider(str, Enum):
    """Supported HRIS providers for data import."""

    PROVIDER_A = "provider_a"
    PROVIDER_B = "provider_b"
    PROVIDER_C = "provider_c"
    CSV = "csv"


class SyncFrequency(str, Enum):
    """How often to sync data."""

    MANUAL = "manual"
    DAILY = "daily"
    WEEKLY = "weekly"


class SyncStatus(str, Enum):
    """Status of a sync operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class HrisSyncConfig:
    """Configuration for an HRIS integration."""

    company_id: str
    provider: HrisProvider
    frequency: SyncFrequency = SyncFrequency.MANUAL
    oauth_token: Optional[str] = None  # stored encrypted in production
    api_endpoint: str = ""
    last_sync_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class EmployeeRecord:
    """Normalised employee record from any HRIS provider."""

    external_id: str
    name: str
    nationality: str  # "citizen", "pr", "foreigner"
    employment_type: str  # "full_time", "part_time", "contract"
    work_pass_type: Optional[str] = None  # "ep", "sp", "wp", None for locals
    department: str = ""
    job_title: str = ""
    monthly_salary: Optional[float] = None
    start_date: Optional[str] = None
    date_of_birth: Optional[str] = None


@dataclass
class HrisSyncResult:
    """Result of a sync operation."""

    sync_id: str
    company_id: str
    provider: HrisProvider
    status: SyncStatus
    total_records: int = 0
    new_records: int = 0
    updated_records: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


# ── In-memory stores ─────────────────────────────────────────

_sync_configs: dict[str, HrisSyncConfig] = {}
_sync_history: list[HrisSyncResult] = []


# ── Provider adapters ────────────────────────────────────────


def _normalise_nationality(raw: str) -> str:
    """Normalise nationality values from different HRIS formats."""
    normalised = raw.lower().strip()
    if normalised in ("singaporean", "citizen", "sc", "singapore citizen"):
        return "citizen"
    if normalised in ("pr", "permanent resident", "spr"):
        return "pr"
    return "foreigner"


def _normalise_employment_type(raw: str) -> str:
    """Normalise employment type values."""
    normalised = raw.lower().strip()
    if normalised in ("full_time", "full-time", "ft", "permanent"):
        return "full_time"
    if normalised in ("part_time", "part-time", "pt"):
        return "part_time"
    return "contract"


def _normalise_pass_type(raw: str) -> Optional[str]:
    """Normalise work pass type values."""
    normalised = raw.lower().strip()
    if normalised in ("ep", "employment pass"):
        return "ep"
    if normalised in ("sp", "s pass", "spass"):
        return "sp"
    if normalised in ("wp", "work permit"):
        return "wp"
    if normalised in ("", "na", "n/a", "none", "local"):
        return None
    return normalised


async def _sync_api_provider(config: HrisSyncConfig) -> list[EmployeeRecord]:
    """Sync employee data from a third-party HRIS API.

    Raises:
        NotImplementedError: API integrations require partnership agreements.
    """
    logger.warning(
        "HRIS API sync requested for company %s (provider: %s) — not yet available. "
        "Use CSV import instead (POST /integrations/hris/import-csv).",
        config.company_id,
        config.provider.value,
    )
    raise NotImplementedError(
        f"{config.provider.value} API integration is not yet available. "
        "Please use CSV import: POST /integrations/hris/import-csv with a CSV file "
        "containing columns: employee_id, name, email, citizenship_status, date_of_birth, "
        "monthly_basic_salary, job_title, department, employment_type, start_date, pass_type."
    )


_PROVIDER_ADAPTERS = {
    HrisProvider.PROVIDER_A: _sync_api_provider,
    HrisProvider.PROVIDER_B: _sync_api_provider,
    HrisProvider.PROVIDER_C: _sync_api_provider,
}


# ── Public API ───────────────────────────────────────────────


async def sync_from_provider(
    sync_id: str,
    company_id: str,
    provider: HrisProvider,
    oauth_token: Optional[str] = None,
) -> HrisSyncResult:
    """Run a sync operation from an HRIS provider.

    Returns the sync result with counts of new/updated records.
    """
    config = _sync_configs.get(company_id)
    if config is None:
        config = HrisSyncConfig(
            company_id=company_id,
            provider=provider,
            oauth_token=oauth_token,
        )
        _sync_configs[company_id] = config

    result = HrisSyncResult(
        sync_id=sync_id,
        company_id=company_id,
        provider=provider,
        status=SyncStatus.IN_PROGRESS,
    )

    adapter = _PROVIDER_ADAPTERS.get(provider)
    if adapter is None:
        result.status = SyncStatus.FAILED
        result.errors.append(f"Unsupported provider: {provider}")
        _sync_history.append(result)
        return result

    try:
        records = await adapter(config)
        result.total_records = len(records)
        result.new_records = len(records)  # simplified — production diffs
        result.status = SyncStatus.COMPLETED
        result.completed_at = datetime.now()
        config.last_sync_at = datetime.now()
    except Exception as e:
        result.status = SyncStatus.FAILED
        result.errors.append(str(e))
        logger.exception("HRIS sync failed for %s/%s", company_id, provider)

    _sync_history.append(result)
    return result


def import_csv(
    sync_id: str,
    company_id: str,
    csv_content: str,
) -> HrisSyncResult:
    """Import employee data from CSV content.

    Expected columns: name, nationality, employment_type, work_pass_type,
    department, job_title, monthly_salary, start_date
    """
    result = HrisSyncResult(
        sync_id=sync_id,
        company_id=company_id,
        provider=HrisProvider.CSV,
        status=SyncStatus.IN_PROGRESS,
    )

    records: list[EmployeeRecord] = []
    reader = csv.DictReader(io.StringIO(csv_content))

    for i, row in enumerate(reader):
        try:
            record = EmployeeRecord(
                external_id=row.get("id", str(i + 1)),
                name=row.get("name", ""),
                nationality=_normalise_nationality(row.get("nationality", "")),
                employment_type=_normalise_employment_type(row.get("employment_type", "")),
                work_pass_type=_normalise_pass_type(row.get("work_pass_type", "")),
                department=row.get("department", ""),
                job_title=row.get("job_title", ""),
                monthly_salary=float(row["monthly_salary"]) if row.get("monthly_salary") else None,
                start_date=row.get("start_date"),
            )
            records.append(record)
        except (ValueError, KeyError) as e:
            result.errors.append(f"Row {i + 1}: {e}")

    result.total_records = len(records)
    result.new_records = len(records)
    result.status = SyncStatus.COMPLETED if not result.errors else SyncStatus.COMPLETED
    result.completed_at = datetime.now()
    _sync_history.append(result)
    return result


def get_sync_history(
    company_id: Optional[str] = None,
) -> list[HrisSyncResult]:
    """Get sync history, optionally filtered by company."""
    history = _sync_history
    if company_id is not None:
        history = [h for h in history if h.company_id == company_id]
    return sorted(history, key=lambda h: h.started_at, reverse=True)
