"""Per-tenant API cost tracker for metered external services.

Tracks costs for MyInfo (S$1/transaction), ACRA (S$5.50/query),
WhatsApp ($0.012/message), LLM calls, and other metered APIs.

T264: Per-Tenant Cost Tracker (Red Team M9)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """A single API cost record."""

    tenant_id: str
    provider: str
    endpoint: str
    cost_cents: int  # Cost in cents (SGD or USD depending on provider)
    currency: str = "SGD"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# Known per-call costs (in cents)
PROVIDER_COSTS: dict[str, int] = {
    "myinfo": 100,  # S$1.00/transaction (beyond free 5K/month)
    "acra": 550,  # S$5.50/query
    "whatsapp": 1,  # ~$0.012/message ≈ 1 cent SGD
    "sms": 5,  # ~$0.05/message
}


class CostTracker:
    """Tracks API consumption costs per tenant.

    Usage::

        tracker = get_cost_tracker()
        tracker.record_cost("company_123", "myinfo", "fetch_person_data", 100)
        monthly = tracker.get_monthly_cost("company_123")
        # {"myinfo": 500, "acra": 1100, "total": 1600}
    """

    def __init__(self):
        self._entries: list[CostEntry] = []
        self._monthly_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_cost(
        self,
        tenant_id: str,
        provider: str,
        endpoint: str = "",
        cost_cents: Optional[int] = None,
        currency: str = "SGD",
    ) -> None:
        """Record an API cost. If cost_cents not provided, uses known provider cost."""
        if cost_cents is None:
            cost_cents = PROVIDER_COSTS.get(provider, 0)

        if cost_cents == 0:
            return  # Free API, no tracking needed

        entry = CostEntry(
            tenant_id=tenant_id,
            provider=provider,
            endpoint=endpoint,
            cost_cents=cost_cents,
            currency=currency,
        )
        self._entries.append(entry)

        month_key = entry.timestamp.strftime("%Y-%m")
        self._monthly_totals[f"{tenant_id}:{month_key}"][provider] += cost_cents

        logger.debug(
            "Cost recorded: %s/%s %d cents for %s",
            tenant_id,
            provider,
            cost_cents,
            endpoint,
        )

    def get_monthly_cost(
        self,
        tenant_id: str,
        year_month: Optional[str] = None,
    ) -> dict:
        """Get cost breakdown by provider for a month.

        Args:
            tenant_id: Company ID.
            year_month: "YYYY-MM" format. Defaults to current month.

        Returns:
            Dict with per-provider costs in cents and total.
        """
        if year_month is None:
            year_month = datetime.now(timezone.utc).strftime("%Y-%m")

        key = f"{tenant_id}:{year_month}"
        provider_costs = dict(self._monthly_totals.get(key, {}))
        total = sum(provider_costs.values())

        return {
            "tenant_id": tenant_id,
            "period": year_month,
            "costs_by_provider": provider_costs,
            "total_cents": total,
            "total_sgd": round(total / 100, 2),
            "currency": "SGD",
        }

    def check_cost_ceiling(
        self,
        tenant_id: str,
        ceiling_cents: int = 5000,  # S$50 default for free tier
    ) -> dict:
        """Check if tenant is approaching or has exceeded cost ceiling.

        Returns warning status and remaining budget.
        """
        monthly = self.get_monthly_cost(tenant_id)
        total = monthly["total_cents"]
        remaining = max(0, ceiling_cents - total)
        pct = (total / ceiling_cents * 100) if ceiling_cents > 0 else 0

        status = "ok"
        if pct >= 100:
            status = "exceeded"
        elif pct >= 80:
            status = "warning"

        if status in ("warning", "exceeded"):
            logger.warning(
                "Cost ceiling %s for %s: %d/%d cents (%.0f%%)",
                status,
                tenant_id,
                total,
                ceiling_cents,
                pct,
            )

        return {
            "tenant_id": tenant_id,
            "status": status,
            "total_cents": total,
            "ceiling_cents": ceiling_cents,
            "remaining_cents": remaining,
            "usage_percent": round(pct, 1),
        }

    def get_recent_entries(
        self,
        tenant_id: str,
        limit: int = 50,
    ) -> list[dict]:
        """Get recent cost entries for a tenant."""
        entries = [e for e in self._entries if e.tenant_id == tenant_id]
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return [
            {
                "provider": e.provider,
                "endpoint": e.endpoint,
                "cost_cents": e.cost_cents,
                "currency": e.currency,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in entries[:limit]
        ]


# Singleton
_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get or create the global cost tracker."""
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
