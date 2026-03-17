"""Integration tests for ConnectorHealthMonitor.

Tests:
- Initial status is UNKNOWN for connectors without circuit breakers
- Record success transitions status to HEALTHY
- Circuit breaker open -> status DOWN
- Circuit breaker half_open -> status DEGRADED
- High error rate -> status DEGRADED
- Summary counts (healthy, degraded, down, unknown)
- Overall status logic
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from hr_advisory.mcp_servers.health import ConnectorHealthMonitor, ConnectorStatus
from hr_advisory.mcp_servers.resilience import CIRCUITS, CircuitBreaker, CircuitState


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


class TestInitialState:
    """Connectors with no activity show expected initial statuses."""

    def test_known_connector_initially_healthy(self, health_monitor: ConnectorHealthMonitor):
        """A known connector with a fresh circuit breaker shows HEALTHY
        (zero error rate, closed circuit)."""
        status = health_monitor.get_status("xero")
        assert status["name"] == "xero"
        assert status["status"] == ConnectorStatus.HEALTHY.value
        assert status["circuit_state"] == "closed"
        assert status["total_calls"] == 0

    def test_unknown_connector_shows_unknown(self, health_monitor: ConnectorHealthMonitor):
        """A connector not in CIRCUITS shows UNKNOWN status."""
        status = health_monitor.get_status("totally_unknown_api")
        assert status["status"] == ConnectorStatus.UNKNOWN.value
        assert status["circuit_state"] is None

    def test_initial_last_success_is_none(self, health_monitor: ConnectorHealthMonitor):
        status = health_monitor.get_status("xero")
        assert status["last_success"] is None


# ---------------------------------------------------------------------------
# Record success
# ---------------------------------------------------------------------------


class TestRecordSuccess:
    """Recording successful calls updates health status."""

    def test_record_success_sets_last_success(self, health_monitor: ConnectorHealthMonitor):
        health_monitor.record_success("xero")
        status = health_monitor.get_status("xero")
        assert status["last_success"] is not None

    def test_record_success_keeps_healthy(self, health_monitor: ConnectorHealthMonitor):
        health_monitor.record_success("xero")
        status = health_monitor.get_status("xero")
        assert status["status"] == ConnectorStatus.HEALTHY.value

    def test_multiple_successes_update_timestamp(self, health_monitor: ConnectorHealthMonitor):
        health_monitor.record_success("xero")
        first = health_monitor.get_status("xero")["last_success"]
        health_monitor.record_success("xero")
        second = health_monitor.get_status("xero")["last_success"]
        assert second >= first


# ---------------------------------------------------------------------------
# Record error
# ---------------------------------------------------------------------------


class TestRecordError:
    """Recording errors updates the last_error field."""

    def test_record_error_sets_last_error(self, health_monitor: ConnectorHealthMonitor):
        health_monitor.record_error("xero", "ConnectionTimeout")
        status = health_monitor.get_status("xero")
        assert status["last_error"] == "ConnectionTimeout"

    def test_latest_error_overwrites_previous(self, health_monitor: ConnectorHealthMonitor):
        health_monitor.record_error("xero", "first error")
        health_monitor.record_error("xero", "second error")
        status = health_monitor.get_status("xero")
        assert status["last_error"] == "second error"


# ---------------------------------------------------------------------------
# Circuit breaker integration
# ---------------------------------------------------------------------------


class TestCircuitBreakerIntegration:
    """Health status reflects circuit breaker state."""

    async def test_open_circuit_shows_down(self, health_monitor: ConnectorHealthMonitor):
        """When the circuit breaker is OPEN, status should be DOWN."""
        circuit = CIRCUITS["xero"]

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit.call(failing)

        assert circuit._state == CircuitState.OPEN
        status = health_monitor.get_status("xero")
        assert status["status"] == ConnectorStatus.DOWN.value
        assert status["circuit_state"] == "open"

    async def test_half_open_circuit_shows_degraded(self, health_monitor: ConnectorHealthMonitor):
        """When the circuit breaker is HALF_OPEN, status should be DEGRADED."""
        circuit = CIRCUITS["xero"]

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit.call(failing)

        # Simulate recovery timeout elapsing
        future_time = time.monotonic() + circuit.recovery_timeout + 1
        with patch("hr_advisory.mcp_servers.resilience.time.monotonic", return_value=future_time):
            status = health_monitor.get_status("xero")
            assert status["status"] == ConnectorStatus.DEGRADED.value
            assert status["circuit_state"] == "half_open"

    async def test_high_error_rate_shows_degraded(self, health_monitor: ConnectorHealthMonitor):
        """Error rate > 30% with closed circuit shows DEGRADED."""
        circuit = CIRCUITS["xero"]

        async def success():
            return "ok"

        async def failing():
            raise ValueError("error")

        # Create a scenario with >30% error rate but below failure threshold
        # xero threshold is 5, so we can have 4 failures without opening
        await circuit.call(success)  # 1 success
        for _ in range(4):
            with pytest.raises(ValueError):
                await circuit.call(failing)
        # 4 failures, 1 success = 80% error rate, but circuit may be open
        # Let's be more precise: 2 success + 1 fail = 33% error rate
        circuit.reset()
        circuit._total_calls = 3
        circuit._total_failures = 1
        # error_rate = 1/3 = 0.33 > 0.3

        status = health_monitor.get_status("xero")
        assert status["status"] == ConnectorStatus.DEGRADED.value

    async def test_recovered_circuit_shows_healthy(self, health_monitor: ConnectorHealthMonitor):
        """After circuit breaker recovers and error rate drops, status returns to HEALTHY.

        Note: The circuit breaker tracks cumulative error rate (_total_failures / _total_calls).
        After tripping (5 failures) and recovering (1 success), the error rate is still
        5/6 = 83%, which triggers DEGRADED. Many additional successful calls are needed
        to bring the error rate below the 30% threshold. This test verifies that a circuit
        in closed state with low error rate shows HEALTHY.
        """
        circuit = CIRCUITS["xero"]

        async def failing():
            raise ConnectionError("down")

        async def success():
            return "ok"

        # Trip the breaker
        for _ in range(circuit.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit.call(failing)

        # Simulate recovery timeout + successful call to close the circuit
        future_time = time.monotonic() + circuit.recovery_timeout + 1
        with patch("hr_advisory.mcp_servers.resilience.time.monotonic", return_value=future_time):
            await circuit.call(success)

        assert circuit.state == CircuitState.CLOSED

        # Bring the cumulative error rate below 30% by adding many successful calls.
        # Currently 5 failures + 1 success = 83% error rate.
        # Need total_calls where 5/total < 0.3, i.e., total > 17.
        for _ in range(20):
            await circuit.call(success)

        assert circuit.error_rate < 0.3
        status = health_monitor.get_status("xero")
        assert status["status"] == ConnectorStatus.HEALTHY.value
        assert status["circuit_state"] == "closed"

    def test_consecutive_failures_count(self, health_monitor: ConnectorHealthMonitor):
        """Status includes consecutive failures from circuit breaker."""
        circuit = CIRCUITS["xero"]
        circuit._failures = 2
        status = health_monitor.get_status("xero")
        assert status["consecutive_failures"] == 2


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    """get_summary() aggregation of all connectors."""

    def test_summary_counts_all_connectors(self, health_monitor: ConnectorHealthMonitor):
        summary = health_monitor.get_summary()
        assert summary["total_connectors"] == len(CIRCUITS)
        assert "healthy" in summary
        assert "degraded" in summary
        assert "down" in summary
        assert "unknown" in summary

    def test_summary_total_matches_individual_counts(self, health_monitor: ConnectorHealthMonitor):
        summary = health_monitor.get_summary()
        total = summary["healthy"] + summary["degraded"] + summary["down"] + summary["unknown"]
        assert total == summary["total_connectors"]

    def test_summary_all_healthy_initially(self, health_monitor: ConnectorHealthMonitor):
        """All connectors with fresh circuit breakers should be healthy."""
        summary = health_monitor.get_summary()
        assert summary["healthy"] == summary["total_connectors"]
        assert summary["down"] == 0
        assert summary["degraded"] == 0
        assert summary["overall_status"] == ConnectorStatus.HEALTHY.value

    async def test_summary_overall_degraded_when_any_down(
        self, health_monitor: ConnectorHealthMonitor
    ):
        """Overall status becomes DEGRADED when any connector is DOWN."""
        circuit = CIRCUITS["xero"]

        async def failing():
            raise ConnectionError("down")

        for _ in range(circuit.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit.call(failing)

        summary = health_monitor.get_summary()
        assert summary["down"] >= 1
        assert summary["overall_status"] == ConnectorStatus.DEGRADED.value

    def test_summary_includes_timestamp(self, health_monitor: ConnectorHealthMonitor):
        summary = health_monitor.get_summary()
        assert "timestamp" in summary
        assert "T" in summary["timestamp"]


# ---------------------------------------------------------------------------
# Get all statuses
# ---------------------------------------------------------------------------


class TestGetAllStatuses:
    """get_all_statuses() returns status for every known connector."""

    def test_returns_list_of_all_connectors(self, health_monitor: ConnectorHealthMonitor):
        statuses = health_monitor.get_all_statuses()
        assert len(statuses) == len(CIRCUITS)
        names = [s["name"] for s in statuses]
        assert "cpf_board" in names
        assert "xero" in names
        assert "dbs" in names

    def test_statuses_sorted_by_name(self, health_monitor: ConnectorHealthMonitor):
        statuses = health_monitor.get_all_statuses()
        names = [s["name"] for s in statuses]
        assert names == sorted(names)

    def test_each_status_has_required_fields(self, health_monitor: ConnectorHealthMonitor):
        statuses = health_monitor.get_all_statuses()
        required_fields = {"name", "status", "last_success", "error_rate", "circuit_state"}
        for status in statuses:
            assert required_fields.issubset(status.keys()), (
                f"Missing fields in status for {status['name']}: "
                f"{required_fields - status.keys()}"
            )
