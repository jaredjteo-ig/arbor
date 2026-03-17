"""Connector health monitoring for all MCP integration servers.

Tracks circuit breaker states, last successful call timestamps,
and error rates for all 38 connectors.

T211: Connector Health Monitor
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from hr_advisory.mcp_servers.resilience import CIRCUITS, get_circuit, CircuitState

logger = logging.getLogger(__name__)


class ConnectorStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class ConnectorHealthMonitor:
    """Real-time health dashboard for all connectors.

    Aggregates circuit breaker state, success timestamps, and error rates
    into a single status per connector.
    """

    def __init__(self):
        self._last_success: dict[str, float] = {}
        self._last_error: dict[str, str] = {}

    def record_success(self, connector_name: str) -> None:
        """Record a successful call for a connector."""
        self._last_success[connector_name] = datetime.now(timezone.utc).timestamp()

    def record_error(self, connector_name: str, error: str) -> None:
        """Record a failed call for a connector."""
        self._last_error[connector_name] = error

    def get_status(self, connector_name: str) -> dict:
        """Get health status for a single connector."""
        circuit = CIRCUITS.get(connector_name)
        if circuit is None:
            return {
                "name": connector_name,
                "status": ConnectorStatus.UNKNOWN.value,
                "last_success": None,
                "error_rate": 0.0,
                "circuit_state": None,
            }

        state = circuit.state
        if state == CircuitState.OPEN:
            status = ConnectorStatus.DOWN
        elif state == CircuitState.HALF_OPEN:
            status = ConnectorStatus.DEGRADED
        elif circuit.error_rate > 0.3:
            status = ConnectorStatus.DEGRADED
        else:
            status = ConnectorStatus.HEALTHY

        last_success = self._last_success.get(connector_name)

        return {
            "name": connector_name,
            "status": status.value,
            "last_success": (
                datetime.fromtimestamp(last_success, tz=timezone.utc).isoformat()
                if last_success
                else None
            ),
            "error_rate": round(circuit.error_rate, 3),
            "circuit_state": state.value,
            "total_calls": circuit._total_calls,
            "consecutive_failures": circuit._failures,
            "last_error": self._last_error.get(connector_name),
        }

    def get_all_statuses(self) -> list[dict]:
        """Get health status for all known connectors."""
        return [self.get_status(name) for name in sorted(CIRCUITS.keys())]

    def get_summary(self) -> dict:
        """Get a summary of overall integration health."""
        statuses = self.get_all_statuses()
        healthy = sum(1 for s in statuses if s["status"] == ConnectorStatus.HEALTHY.value)
        degraded = sum(1 for s in statuses if s["status"] == ConnectorStatus.DEGRADED.value)
        down = sum(1 for s in statuses if s["status"] == ConnectorStatus.DOWN.value)
        unknown = sum(1 for s in statuses if s["status"] == ConnectorStatus.UNKNOWN.value)

        overall = ConnectorStatus.HEALTHY
        if down > 0:
            overall = ConnectorStatus.DEGRADED
        if down > len(statuses) * 0.5:
            overall = ConnectorStatus.DOWN

        return {
            "overall_status": overall.value,
            "total_connectors": len(statuses),
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "unknown": unknown,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Singleton
_monitor: Optional[ConnectorHealthMonitor] = None


def get_health_monitor() -> ConnectorHealthMonitor:
    """Get or create the global health monitor."""
    global _monitor
    if _monitor is None:
        _monitor = ConnectorHealthMonitor()
    return _monitor
