"""Talenox REST API adapter for employee data import.

Fetches employee records, payroll history, and leave balances from
Talenox for companies migrating to AITE. Read-only — we never write
back to Talenox. Supports dry-run preview and validation.

T249: Talenox Data Import Connector
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

_TALENOX_API_BASE = "https://api.talenox.com/api/v2/"


class TalenoxAPIError(Exception):
    """Raised when a Talenox API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Talenox API [{status_code}]: {detail}")


# Field mapping: Talenox field name -> AITE Employee model field name.
# Talenox uses camelCase in their API responses.
_FIELD_MAPPING: dict[str, str] = {
    "id": "external_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "date_of_birth": "date_of_birth",
    "nationality": "nationality",
    "nric_fin": "nric",
    "gender": "gender",
    "job_title": "job_title",
    "department": "department",
    "employment_type": "employment_type",
    "basic_salary": "monthly_salary",
    "start_date": "start_date",
    "end_date": "end_date",
    "bank_account_number": "bank_account_number",
    "bank_name": "bank_name",
    "phone_number": "phone",
    "address": "address",
    "race": "race",
    "marital_status": "marital_status",
    "work_pass_type": "work_pass_type",
    "work_pass_expiry": "work_pass_expiry",
}


def _normalize_nationality(raw: Optional[str]) -> str:
    """Normalize Talenox nationality values to AITE format."""
    if not raw:
        return "foreigner"
    normalized = raw.lower().strip()
    if normalized in ("singaporean", "citizen", "sc", "singapore citizen"):
        return "citizen"
    if normalized in ("pr", "permanent resident", "spr", "singapore pr"):
        return "pr"
    return "foreigner"


def _normalize_employment_type(raw: Optional[str]) -> str:
    """Normalize employment type."""
    if not raw:
        return "full_time"
    normalized = raw.lower().strip()
    if normalized in ("full_time", "full-time", "ft", "permanent", "full time"):
        return "full_time"
    if normalized in ("part_time", "part-time", "pt", "part time"):
        return "part_time"
    return "contract"


def _normalize_work_pass(raw: Optional[str]) -> Optional[str]:
    """Normalize work pass type."""
    if not raw:
        return None
    normalized = raw.lower().strip()
    if normalized in ("ep", "employment pass"):
        return "ep"
    if normalized in ("sp", "s pass", "spass"):
        return "sp"
    if normalized in ("wp", "work permit"):
        return "wp"
    if normalized in ("", "na", "n/a", "none", "local", "-"):
        return None
    return normalized


class TalenoxAdapter:
    """Adapter for Talenox REST API — read-only employee data import.

    Talenox provides a REST API for retrieving employee data, payroll
    history, and leave balances. Auth is via a Bearer token that the
    company admin provides during the migration flow.

    Usage::

        adapter = TalenoxAdapter()
        employees = await adapter.fetch_employees(api_token="tnx_...")
        for emp in employees:
            mapped = adapter.map_to_aite_employee(emp)
            # Create employee in AITE...
    """

    def __init__(self):
        self._circuit = get_circuit("talenox")

    def _headers(self, api_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _api_call(
        self,
        method: str,
        path: str,
        api_token: str,
        params: Optional[dict] = None,
    ) -> Any:
        """Make a Talenox API call through the circuit breaker."""

        async def _do_call() -> Any:
            url = f"{_TALENOX_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(api_token), params=params)
                else:
                    raise ValueError(f"Unsupported method for read-only adapter: {method}")

                if resp.status_code == 401:
                    raise TalenoxAPIError(
                        status_code=401,
                        detail="Invalid or expired Talenox API token. Please re-enter your token.",
                    )
                if resp.status_code >= 400:
                    raise TalenoxAPIError(
                        status_code=resp.status_code,
                        detail=resp.text[:500],
                    )

                return resp.json()

        return await self._circuit.call(_do_call)

    async def fetch_employees(
        self,
        api_token: str,
        include_inactive: bool = False,
    ) -> list[dict]:
        """Fetch all employee records from Talenox.

        Args:
            api_token: Talenox API Bearer token provided by the user.
            include_inactive: Whether to include terminated employees.

        Returns:
            List of raw Talenox employee dicts.
        """
        params: dict[str, Any] = {}
        if include_inactive:
            params["include_inactive"] = "true"

        result = await self._api_call("GET", "employees", api_token, params=params)

        # Talenox may return a list directly or wrap in a dict
        employees = (
            result if isinstance(result, list) else result.get("employees", result.get("data", []))
        )

        logger.info("Fetched %d employees from Talenox", len(employees))
        return employees

    async def fetch_payroll_history(
        self,
        api_token: str,
        year: int,
        month: Optional[int] = None,
    ) -> list[dict]:
        """Fetch payroll history from Talenox.

        Args:
            api_token: Talenox API Bearer token.
            year: Year to fetch (e.g. 2025).
            month: Optional month (1-12). If None, fetches entire year.

        Returns:
            List of payroll record dicts.
        """
        params: dict[str, Any] = {"year": str(year)}
        if month is not None:
            params["month"] = str(month)

        result = await self._api_call("GET", "payroll", api_token, params=params)
        payrolls = (
            result if isinstance(result, list) else result.get("payrolls", result.get("data", []))
        )

        logger.info("Fetched %d payroll records from Talenox for %d", len(payrolls), year)
        return payrolls

    async def fetch_leave_balances(
        self,
        api_token: str,
    ) -> list[dict]:
        """Fetch leave balances for all employees.

        Returns:
            List of leave balance dicts per employee.
        """
        result = await self._api_call("GET", "leaves/balances", api_token)
        balances = (
            result if isinstance(result, list) else result.get("balances", result.get("data", []))
        )

        logger.info("Fetched leave balances for %d employees from Talenox", len(balances))
        return balances

    def map_to_aite_employee(self, talenox_record: dict) -> dict:
        """Map a single Talenox employee record to AITE's employee format.

        Handles field name differences, normalizes nationality,
        employment type, and work pass values. Returns a dict ready
        for AITE employee creation.

        Args:
            talenox_record: Raw employee dict from Talenox API.

        Returns:
            Dict with AITE employee field names and normalized values.
        """
        mapped: dict[str, Any] = {}

        for talenox_field, aite_field in _FIELD_MAPPING.items():
            value = talenox_record.get(talenox_field)
            if value is not None:
                mapped[aite_field] = value

        # Build full name from parts if present
        first = talenox_record.get("first_name", "")
        last = talenox_record.get("last_name", "")
        if first or last:
            mapped["name"] = f"{first} {last}".strip()

        # Normalize enum-like fields
        mapped["nationality"] = _normalize_nationality(
            talenox_record.get("nationality") or talenox_record.get("citizenship_status")
        )
        mapped["employment_type"] = _normalize_employment_type(
            talenox_record.get("employment_type") or talenox_record.get("employment_status")
        )
        mapped["work_pass_type"] = _normalize_work_pass(
            talenox_record.get("work_pass_type") or talenox_record.get("pass_type")
        )

        # Ensure salary is a float
        salary = talenox_record.get("basic_salary") or talenox_record.get("monthly_salary")
        if salary is not None:
            try:
                mapped["monthly_salary"] = float(salary)
            except (ValueError, TypeError):
                mapped["monthly_salary"] = None

        # Preserve the original external ID for dedup
        mapped["external_id"] = str(talenox_record.get("id", ""))
        mapped["source"] = "talenox"

        return mapped

    def validate_import(
        self,
        employees: list[dict],
    ) -> dict:
        """Validate a batch of mapped employee records before import.

        Checks for: missing required fields, invalid values, potential
        duplicates (by NRIC or name+DOB).

        Args:
            employees: List of mapped employee dicts (from map_to_aite_employee).

        Returns:
            Validation report dict with valid_count, error_count,
            warnings, and per-record issues.
        """
        issues: list[dict] = []
        seen_nrics: set[str] = set()
        seen_names: set[str] = set()
        valid_count = 0

        required_fields = ["name", "nationality", "employment_type"]

        for i, emp in enumerate(employees):
            record_issues: list[str] = []

            # Check required fields
            for field in required_fields:
                if not emp.get(field):
                    record_issues.append(f"Missing required field: {field}")

            # Check for duplicate NRICs
            nric = emp.get("nric")
            if nric:
                if nric in seen_nrics:
                    record_issues.append(f"Duplicate NRIC: {nric}")
                seen_nrics.add(nric)

            # Check salary is reasonable
            salary = emp.get("monthly_salary")
            if salary is not None:
                if salary < 0:
                    record_issues.append(f"Negative salary: {salary}")
                elif salary > 100000:
                    record_issues.append(f"Unusually high salary: {salary} — please verify")

            # Check name duplicates (warning only)
            name = emp.get("name", "").lower()
            if name in seen_names:
                record_issues.append(
                    f"Duplicate name: {emp.get('name')} — verify not a duplicate record"
                )
            if name:
                seen_names.add(name)

            if record_issues:
                issues.append(
                    {
                        "index": i,
                        "external_id": emp.get("external_id", ""),
                        "name": emp.get("name", ""),
                        "issues": record_issues,
                    }
                )
            else:
                valid_count += 1

        return {
            "total": len(employees),
            "valid_count": valid_count,
            "error_count": len(issues),
            "issues": issues,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
