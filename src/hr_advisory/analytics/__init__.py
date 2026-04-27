"""Analytics engine (T054).

Provides analytics for platform users:
- Workforce composition overview
- Compliance status tracking
- Cost modeling (CPF, levy projections)
- Advisory usage metrics
"""

from hr_advisory.analytics.engine import (
    WorkforceAnalytics,
    ComplianceMetrics,
    CostProjection,
    UsageMetrics,
    get_workforce_analytics,
    get_compliance_metrics,
    get_cost_projection,
    get_usage_metrics,
)

__all__ = [
    "WorkforceAnalytics",
    "ComplianceMetrics",
    "CostProjection",
    "UsageMetrics",
    "get_workforce_analytics",
    "get_compliance_metrics",
    "get_cost_projection",
    "get_usage_metrics",
]
