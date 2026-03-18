"""SkillsFuture SSG Developer Portal API adapter.

Search SkillsFuture course catalog, calculate training grant
eligibility, get course details, and initiate SFC credit payments.
Unique SG differentiator — employees can discover courses and
check government training grants directly within Arbor.

T251: SkillsFuture SSG Integration (G11)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)

# SSG Developer Portal API endpoints.
# Actual production endpoints require SSG approval.
_SSG_API_BASE = "https://public-api.ssg-wsg.gov.sg/"

# SkillsFuture Credit (SFC) payment gateway.
_SFC_PAYMENT_GATEWAY = (
    "https://www.myskillsfuture.gov.sg/content/portal/en/training-exchange/course-registration.html"
)


class SSGAPIError(Exception):
    """Raised when an SSG API call fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"SSG API [{status_code}]: {detail}")


# Training grant eligibility rules (simplified).
# Full rules are complex and depend on employee age, citizenship,
# company size, course certification level, etc.
# This provides a reasonable estimate — exact amounts require
# SSG grant eligibility API.
_GRANT_RULES: dict[str, dict[str, Any]] = {
    "citizen": {
        "base_rate": 0.70,  # 70% of course fees (up to cap)
        "mid_career_rate": 0.90,  # 90% for age 40+ (Mid-Career Enhanced Subsidy)
        "mid_career_age": 40,
        "max_grant_per_course": 10000,
        "sfc_eligible": True,
    },
    "pr": {
        "base_rate": 0.70,
        "mid_career_rate": 0.90,
        "mid_career_age": 40,
        "max_grant_per_course": 10000,
        "sfc_eligible": False,  # SFC only for citizens
    },
    "foreigner": {
        "base_rate": 0.0,
        "mid_career_rate": 0.0,
        "mid_career_age": 0,
        "max_grant_per_course": 0,
        "sfc_eligible": False,
    },
}


class SkillsFutureAdapter:
    """Adapter for SkillsFuture Singapore (SSG) Developer Portal APIs.

    Provides course search, grant calculation, and SFC payment initiation.
    API access requires SSG approval and an API key.

    Usage::

        adapter = SkillsFutureAdapter()
        courses = await adapter.search_courses("employment law")
        details = await adapter.get_course_details("CRS-12345")
        grant = adapter.calculate_grant(
            employee_data={"nationality": "citizen", "age": 42},
            course_fee=500.00,
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
    ):
        self._api_key = api_key or os.environ.get("SSG_API_KEY", "")
        self._circuit = get_circuit("skillsfuture")

        if not self._api_key:
            logger.warning("SSG_API_KEY not set — SkillsFuture adapter will fail on API calls")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    async def _api_call(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json_body: Optional[dict] = None,
    ) -> Any:
        """Make an SSG API call through the circuit breaker."""

        async def _do_call() -> Any:
            url = f"{_SSG_API_BASE}{path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    resp = await client.get(url, headers=self._headers(), params=params)
                elif method == "POST":
                    resp = await client.post(url, json=json_body, headers=self._headers())
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                if resp.status_code == 401:
                    raise SSGAPIError(
                        status_code=401,
                        detail="Invalid SSG API key. Contact SSG Developer Portal for access.",
                    )
                if resp.status_code >= 400:
                    raise SSGAPIError(
                        status_code=resp.status_code,
                        detail=resp.text[:500],
                    )

                return resp.json()

        return await self._circuit.call(_do_call)

    # ── Course search ────────────────────────────────────────────

    async def search_courses(
        self,
        query: str,
        filters: Optional[dict] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Search the SSG course catalog.

        Args:
            query: Free-text search query (e.g. "data analytics",
                "employment law", "workplace safety").
            filters: Optional filter dict. Supported keys:
                - training_provider: Provider name.
                - course_type: "Classroom", "E-Learning", "Blended".
                - funding_type: "SkillsFuture", "WSQ".
                - min_duration_hours: Minimum course duration.
                - max_duration_hours: Maximum course duration.
                - area_of_training: e.g., "Information Technology".
            page: Page number (1-indexed).
            page_size: Results per page (max 50).

        Returns:
            Dict with courses list and pagination metadata.
        """
        params: dict[str, Any] = {
            "keyword": query,
            "page": str(page),
            "pageSize": str(min(page_size, 50)),
        }

        if filters:
            if filters.get("training_provider"):
                params["trainingProvider"] = filters["training_provider"]
            if filters.get("course_type"):
                params["modeOfTraining"] = filters["course_type"]
            if filters.get("funding_type"):
                params["fundingType"] = filters["funding_type"]
            if filters.get("area_of_training"):
                params["areaOfTraining"] = filters["area_of_training"]

        result = await self._api_call("GET", "courses", params=params)

        # Normalize response format
        raw_courses = result.get("data", result.get("courses", []))
        courses = [self._normalize_course(c) for c in raw_courses]

        total_count = result.get("totalCount", result.get("total", len(courses)))
        total_pages = (total_count + page_size - 1) // page_size if total_count else 1

        logger.info(
            "SSG course search '%s': %d results (page %d/%d)",
            query,
            len(courses),
            page,
            total_pages,
        )

        return {
            "courses": courses,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }

    async def get_course_details(self, course_id: str) -> dict:
        """Get detailed information about a specific course.

        Args:
            course_id: SSG course reference number (e.g. "CRS-N-0048636").

        Returns:
            Detailed course dict with fee, schedule, provider, etc.
        """
        result = await self._api_call("GET", f"courses/{course_id}")
        course = result.get("data", result) if isinstance(result, dict) else result
        return self._normalize_course_detail(course)

    def _normalize_course(self, raw: dict) -> dict:
        """Normalize an SSG course record to a consistent format."""
        return {
            "course_id": raw.get("referenceNumber") or raw.get("courseId") or raw.get("id", ""),
            "title": raw.get("title") or raw.get("courseName", ""),
            "provider": raw.get("trainingProvider") or raw.get("provider", ""),
            "mode": raw.get("modeOfTraining") or raw.get("courseType", ""),
            "duration_hours": raw.get("totalTrainingDuration") or raw.get("durationHours"),
            "fee": self._parse_fee(raw.get("totalCostOfTrainingPerTrainee") or raw.get("fee")),
            "funding_eligible": raw.get("fundingEligible", True),
            "area_of_training": raw.get("areaOfTraining") or raw.get("category", ""),
        }

    def _normalize_course_detail(self, raw: dict) -> dict:
        """Normalize detailed course information."""
        base = self._normalize_course(raw)
        base.update(
            {
                "description": raw.get("courseObjective") or raw.get("description", ""),
                "content_outline": raw.get("courseContentDescription")
                or raw.get("contentOutline", ""),
                "entry_requirements": raw.get("entryRequirement") or raw.get("prerequisites", ""),
                "certification": raw.get("certificationName") or raw.get("certification", ""),
                "language": raw.get("language") or raw.get("medium", "English"),
                "provider_uen": raw.get("trainingProviderUen") or raw.get("providerUen", ""),
                "website": raw.get("url") or raw.get("website", ""),
                "schedules": raw.get("runs") or raw.get("schedules", []),
                "nett_fee_after_subsidy": self._parse_fee(
                    raw.get("nettFee") or raw.get("nettFeeAfterSubsidy")
                ),
            }
        )
        return base

    @staticmethod
    def _parse_fee(raw: Any) -> Optional[float]:
        """Parse a fee value from various formats."""
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            cleaned = raw.strip().replace("$", "").replace(",", "").replace("S", "").strip()
            if not cleaned or cleaned == "-":
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    # ── Grant calculation ────────────────────────────────────────

    def calculate_grant(
        self,
        employee_data: dict,
        course_fee: float,
        course_id: Optional[str] = None,
    ) -> dict:
        """Calculate estimated training grant eligibility.

        This is a local estimate based on known SSG grant rules. For
        exact amounts, the SSG grant eligibility API should be used
        (requires the employee's NRIC with consent).

        Args:
            employee_data: Dict with at minimum:
                - nationality: "citizen", "pr", or "foreigner".
                - age: Employee age (for mid-career subsidy check).
            course_fee: Total course fee in SGD.
            course_id: Optional course reference for enriched response.

        Returns:
            Grant estimate dict with amounts and eligibility details.
        """
        nationality = employee_data.get("nationality", "foreigner")
        age = employee_data.get("age", 0)
        rules = _GRANT_RULES.get(nationality, _GRANT_RULES["foreigner"])

        # Determine applicable rate
        if age >= rules["mid_career_age"] and rules["mid_career_rate"] > 0:
            rate = rules["mid_career_rate"]
            subsidy_type = "Mid-Career Enhanced Subsidy"
        else:
            rate = rules["base_rate"]
            subsidy_type = "Standard SkillsFuture Subsidy"

        # Calculate grant amount
        raw_grant = course_fee * rate
        grant_amount = min(raw_grant, rules["max_grant_per_course"])
        out_of_pocket = max(0, course_fee - grant_amount)

        return {
            "course_id": course_id,
            "course_fee": course_fee,
            "nationality": nationality,
            "age": age,
            "subsidy_type": subsidy_type,
            "subsidy_rate": rate,
            "estimated_grant": round(grant_amount, 2),
            "estimated_out_of_pocket": round(out_of_pocket, 2),
            "sfc_eligible": rules["sfc_eligible"],
            "note": (
                "This is an estimate. Exact grant amount depends on course certification level, "
                "training provider, and individual eligibility. Check with SSG for confirmation."
            ),
            "disclaimer": (
                "Grant calculations are estimates based on published SSG guidelines. "
                "Actual eligibility and amounts are determined by SSG."
            ),
        }

    # ── SFC payment ──────────────────────────────────────────────

    def initiate_sfc_payment(
        self,
        employee_id: str,
        course_id: str,
        course_title: str = "",
    ) -> dict:
        """Generate a redirect URL for SkillsFuture Credit payment.

        SFC payment is handled entirely by the MySkillsFuture portal.
        We generate the URL and redirect the employee; Arbor does not
        handle any credit card or SFC balance data.

        Only Singapore citizens are eligible for SFC.

        Args:
            employee_id: Arbor employee ID (for audit trail).
            course_id: SSG course reference number.
            course_title: Course title for display.

        Returns:
            Dict with redirect URL and instructions.
        """
        # Build the MySkillsFuture portal URL with course pre-selected
        redirect_url = f"{_SFC_PAYMENT_GATEWAY}?courseId={course_id}"

        logger.info(
            "SFC payment initiated for employee=%s course=%s",
            employee_id,
            course_id,
        )

        return {
            "redirect_url": redirect_url,
            "course_id": course_id,
            "course_title": course_title,
            "instructions": (
                "You will be redirected to the MySkillsFuture portal to complete "
                "payment using your SkillsFuture Credit. You will need to log in "
                "with your Singpass. Only Singapore citizens are eligible for SFC."
            ),
            "employee_id": employee_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
