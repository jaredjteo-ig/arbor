"""HReasily API adapter for employee data import.

Fetches employee records, payroll history, and leave balances from
HReasily for companies migrating to Arbor. Read-only — same pattern
as the Talenox adapter. HReasily uses a unified REST API.

T250: HReasily Data Import Connector
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

# HReasily has a unified API endpoint.
_HREASILY_API_BASE = "https://api.hreasily.com/api/v1/"


class HREasilyAPIError(Exception):
    """Raised when an HReasily API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HReasily API [{status_code}]: {detail}")


# Field mapping: HReasily field name -> Arbor Employee model field name.
_FIELD_MAPPING: dict[str, str] = {
    "id": "external_id",
    "first_name": "first_name",
    "last_name": "last_name",
    "full_name": "name",
    "email": "email",
    "date_of_birth": "date_of_birth",
    "nationality": "nationality",
    "nric": "nric",
    "ic_number": "nric",
    "gender": "gender",
    "designation": "job_title",
    "department_name": "department",
    "employment_type": "employment_type",
    "basic_pay": "monthly_salary",
    "join_date": "start_date",
    "resign_date": "end_date",
    "bank_account_no": "bank_account_number",
    "bank_name": "bank_name",
    "phone": "phone",
    "mobile": "phone",
    "address": "address",
    "race": "race",
    "marital_status": "marital_status",
    "pass_type": "work_pass_type",
    "pass_expiry_date": "work_pass_expiry",
}


def _normalize_nationality(raw: Optional[str]) -> str:
    """Normalize HReasily nationality values to Arbor format."""
    if not raw:
        return "foreigner"
    normalized = raw.lower().strip()
    if normalized in ("singaporean", "citizen", "sc", "singapore citizen", "sg citizen"):
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


class HREasilyAdapter:
    """Adapter for HReasily REST API — read-only employee data import.

    HReasily provides a unified REST API for employee, payroll, and
    leave data. Auth is via a Bearer token provided by the company
    admin during migration.

    Same interface pattern as TalenoxAdapter for consistency.

    Usage::

        adapter = HREasilyAdapter()
        employees = await adapter.fetch_employees(api_token="hre_...")
        for emp in employees:
            mapped = adapter.map_to_arbor_employee(emp)
    """

    def __init__(self):
        self._circuit = get_circuit("hreasily")

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
        """Make an HReasily API call through the circuit breaker."""

        async def _do_call() -> Any:
            url = f"{_HREASILY_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(api_token), params=params)
                else:
                    raise ValueError(f"Unsupported method for read-only adapter: {method}")

                if resp.status_code == 401:
                    raise HREasilyAPIError(
                        status_code=401,
                        detail="Invalid or expired HReasily API token. Please re-enter your token.",
                    )
                if resp.status_code == 403:
                    raise HREasilyAPIError(
                        status_code=403,
                        detail="API access denied. Check your HReasily subscription includes API access.",
                    )
                if resp.status_code >= 400:
                    raise HREasilyAPIError(
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
        """Fetch all employee records from HReasily.

        Args:
            api_token: HReasily API Bearer token provided by the user.
            include_inactive: Whether to include terminated employees.

        Returns:
            List of raw HReasily employee dicts.
        """
        params: dict[str, Any] = {}
        if include_inactive:
            params["status"] = "all"
        else:
            params["status"] = "active"

        # HReasily may paginate — fetch all pages
        all_employees: list[dict] = []
        page = 1
        while True:
            params["page"] = str(page)
            params["per_page"] = "100"

            result = await self._api_call("GET", "employees", api_token, params=params)

            # Handle both list and paginated dict responses
            if isinstance(result, list):
                all_employees.extend(result)
                break  # No pagination metadata
            else:
                employees = result.get("employees", result.get("data", []))
                all_employees.extend(employees)

                # Check for next page
                meta = result.get("meta", result.get("pagination", {}))
                total_pages = meta.get("total_pages", meta.get("last_page", 1))
                if page >= total_pages:
                    break
                page += 1

        logger.info("Fetched %d employees from HReasily", len(all_employees))
        return all_employees

    async def fetch_payroll_history(
        self,
        api_token: str,
        year: int,
        month: Optional[int] = None,
    ) -> list[dict]:
        """Fetch payroll history from HReasily.

        Args:
            api_token: HReasily API Bearer token.
            year: Year to fetch.
            month: Optional month (1-12).

        Returns:
            List of payroll record dicts.
        """
        params: dict[str, Any] = {"year": str(year)}
        if month is not None:
            params["month"] = str(month)

        result = await self._api_call("GET", "payroll/history", api_token, params=params)
        payrolls = (
            result if isinstance(result, list) else result.get("payrolls", result.get("data", []))
        )

        logger.info("Fetched %d payroll records from HReasily for %d", len(payrolls), year)
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

        logger.info("Fetched leave balances for %d employees from HReasily", len(balances))
        return balances

    def map_to_arbor_employee(self, hreasily_record: dict) -> dict:
        """Map a single HReasily employee record to Arbor's employee format.

        Args:
            hreasily_record: Raw employee dict from HReasily API.

        Returns:
            Dict with Arbor employee field names and normalized values.
        """
        mapped: dict[str, Any] = {}

        for hre_field, arbor_field in _FIELD_MAPPING.items():
            value = hreasily_record.get(hre_field)
            if value is not None and arbor_field not in mapped:
                mapped[arbor_field] = value

        # Build full name if not already present
        if "name" not in mapped:
            first = hreasily_record.get("first_name", "")
            last = hreasily_record.get("last_name", "")
            if first or last:
                mapped["name"] = f"{first} {last}".strip()

        # Normalize enum-like fields
        mapped["nationality"] = _normalize_nationality(
            hreasily_record.get("nationality") or hreasily_record.get("citizenship_status")
        )
        mapped["employment_type"] = _normalize_employment_type(
            hreasily_record.get("employment_type") or hreasily_record.get("employment_status")
        )
        mapped["work_pass_type"] = _normalize_work_pass(
            hreasily_record.get("pass_type") or hreasily_record.get("work_pass_type")
        )

        # Ensure salary is a float
        salary = (
            hreasily_record.get("basic_pay")
            or hreasily_record.get("basic_salary")
            or hreasily_record.get("monthly_salary")
        )
        if salary is not None:
            try:
                mapped["monthly_salary"] = float(salary)
            except (ValueError, TypeError):
                mapped["monthly_salary"] = None

        mapped["external_id"] = str(hreasily_record.get("id", ""))
        mapped["source"] = "hreasily"

        return mapped

    def validate_import(
        self,
        employees: list[dict],
    ) -> dict:
        """Validate a batch of mapped employee records before import.

        Same validation logic as TalenoxAdapter for consistency.

        Args:
            employees: List of mapped employee dicts.

        Returns:
            Validation report dict.
        """
        issues: list[dict] = []
        seen_nrics: set[str] = set()
        seen_names: set[str] = set()
        valid_count = 0

        required_fields = ["name", "nationality", "employment_type"]

        for i, emp in enumerate(employees):
            record_issues: list[str] = []

            for field in required_fields:
                if not emp.get(field):
                    record_issues.append(f"Missing required field: {field}")

            nric = emp.get("nric")
            if nric:
                if nric in seen_nrics:
                    record_issues.append(f"Duplicate NRIC: {nric}")
                seen_nrics.add(nric)

            salary = emp.get("monthly_salary")
            if salary is not None:
                if salary < 0:
                    record_issues.append(f"Negative salary: {salary}")
                elif salary > 100000:
                    record_issues.append(f"Unusually high salary: {salary} — please verify")

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
