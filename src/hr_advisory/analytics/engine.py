"""Analytics Engine (T054).

Computes analytics for platform users including workforce
composition, compliance trends, cost projections, and usage metrics.

In production, backed by DataFlow aggregate queries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class WorkforceBreakdown:
    """Breakdown of workforce by a single dimension."""

    label: str
    count: int
    percentage: float


@dataclass
class WorkforceAnalytics:
    """Workforce composition overview for a company."""

    company_id: str
    total_headcount: int
    by_nationality: list[WorkforceBreakdown]
    by_employment_type: list[WorkforceBreakdown]
    by_pass_type: list[WorkforceBreakdown]
    by_department: list[WorkforceBreakdown]
    foreign_worker_ratio: float
    drc_utilisation: float  # percentage of DRC quota used
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class ComplianceTrend:
    """Single data point in compliance trend."""

    date: str  # YYYY-MM-DD
    score: int
    risk_tier: str


@dataclass
class ComplianceMetrics:
    """Compliance status tracking over time."""

    company_id: str
    current_score: int
    current_risk_tier: str
    trend: list[ComplianceTrend]
    open_issues: int
    resolved_this_month: int
    by_domain: dict[str, int]  # domain → score
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class CostLineItem:
    """Single line item in cost projection."""

    label: str
    current_monthly: float
    projected_monthly: float
    change_percentage: float


@dataclass
class CostProjection:
    """Cost modeling for CPF, levy, and hiring scenarios."""

    company_id: str
    total_monthly_cpf: float
    total_monthly_levy: float
    total_monthly_cost: float
    line_items: list[CostLineItem]
    scenario_description: str = ""
    generated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TopQuery:
    """A frequently asked query topic."""

    topic: str
    domain: str
    count: int
    avg_satisfaction: float


@dataclass
class UsageMetrics:
    """Advisory usage analytics."""

    company_id: str
    total_queries: int
    queries_this_month: int
    queries_by_domain: dict[str, int]
    top_queries: list[TopQuery]
    avg_confidence: float
    positive_feedback_rate: float
    documents_generated: int
    calculators_used: int
    generated_at: datetime = field(default_factory=datetime.now)


# ── Analytics computation ────────────────────────────────────


def _make_breakdown(
    items: dict[str, int],
    total: int,
) -> list[WorkforceBreakdown]:
    """Create breakdown list from counts dict."""
    return [
        WorkforceBreakdown(
            label=label,
            count=count,
            percentage=round(count / total * 100, 1) if total > 0 else 0.0,
        )
        for label, count in sorted(items.items(), key=lambda x: x[1], reverse=True)
    ]


def get_workforce_analytics(
    company_id: str,
    headcount_local: int = 0,
    headcount_pr: int = 0,
    headcount_ep: int = 0,
    headcount_sp: int = 0,
    headcount_wp: int = 0,
    departments: Optional[dict[str, int]] = None,
) -> WorkforceAnalytics:
    """Compute workforce analytics for a company.

    In production, pulls data from DataFlow Company + Employee models.
    """
    total = headcount_local + headcount_pr + headcount_ep + headcount_sp + headcount_wp
    foreign_count = headcount_ep + headcount_sp + headcount_wp
    local_count = headcount_local + headcount_pr

    nationality_counts = {
        "Singapore Citizen": headcount_local,
        "Permanent Resident": headcount_pr,
        "Foreigner": foreign_count,
    }

    pass_counts: dict[str, int] = {}
    if headcount_ep > 0:
        pass_counts["Employment Pass"] = headcount_ep
    if headcount_sp > 0:
        pass_counts["S Pass"] = headcount_sp
    if headcount_wp > 0:
        pass_counts["Work Permit"] = headcount_wp
    if local_count > 0:
        pass_counts["Local (no pass)"] = local_count

    foreign_ratio = foreign_count / total if total > 0 else 0.0
    drc_used = (foreign_count / local_count * 100) if local_count > 0 else 0.0

    return WorkforceAnalytics(
        company_id=company_id,
        total_headcount=total,
        by_nationality=_make_breakdown(nationality_counts, total),
        by_employment_type=_make_breakdown({"Full-time": total}, total),
        by_pass_type=_make_breakdown(pass_counts, total),
        by_department=_make_breakdown(departments or {}, total),
        foreign_worker_ratio=round(foreign_ratio, 3),
        drc_utilisation=round(drc_used, 1),
    )


def get_compliance_metrics(
    company_id: str,
    current_score: int = 85,
    trend_data: Optional[list[ComplianceTrend]] = None,
    open_issues: int = 0,
    resolved_this_month: int = 0,
    domain_scores: Optional[dict[str, int]] = None,
) -> ComplianceMetrics:
    """Get compliance metrics for a company.

    In production, aggregated from ComplianceCheck DataFlow model.
    """
    if current_score >= 80:
        risk_tier = "green"
    elif current_score >= 50:
        risk_tier = "amber"
    else:
        risk_tier = "red"

    return ComplianceMetrics(
        company_id=company_id,
        current_score=current_score,
        current_risk_tier=risk_tier,
        trend=trend_data or [],
        open_issues=open_issues,
        resolved_this_month=resolved_this_month,
        by_domain=domain_scores or {},
    )


def get_cost_projection(
    company_id: str,
    monthly_cpf_employer: float = 0.0,
    monthly_cpf_employee: float = 0.0,
    monthly_levy: float = 0.0,
    scenario_items: Optional[list[CostLineItem]] = None,
    scenario_description: str = "",
) -> CostProjection:
    """Generate cost projection for a company.

    In production, computed from CPF calculator + levy calculator
    using actual employee data from DataFlow.
    """
    total_cpf = monthly_cpf_employer + monthly_cpf_employee
    total = total_cpf + monthly_levy

    return CostProjection(
        company_id=company_id,
        total_monthly_cpf=round(total_cpf, 2),
        total_monthly_levy=round(monthly_levy, 2),
        total_monthly_cost=round(total, 2),
        line_items=scenario_items or [],
        scenario_description=scenario_description,
    )


def get_usage_metrics(
    company_id: str,
    total_queries: int = 0,
    queries_this_month: int = 0,
    queries_by_domain: Optional[dict[str, int]] = None,
    top_queries: Optional[list[TopQuery]] = None,
    avg_confidence: float = 0.0,
    positive_feedback_rate: float = 0.0,
    documents_generated: int = 0,
    calculators_used: int = 0,
) -> UsageMetrics:
    """Get advisory usage metrics for a company.

    In production, aggregated from AdvisorySession + UserFeedback
    DataFlow models.
    """
    return UsageMetrics(
        company_id=company_id,
        total_queries=total_queries,
        queries_this_month=queries_this_month,
        queries_by_domain=queries_by_domain or {},
        top_queries=top_queries or [],
        avg_confidence=avg_confidence,
        positive_feedback_rate=positive_feedback_rate,
        documents_generated=documents_generated,
        calculators_used=calculators_used,
    )
