"""Shared fixtures for MCP integration server tests.

Provides:
- Isolated ArborMCPServer instances with registered test tools
- Tenant contexts for multi-tenant testing
- Pre-configured ExternalTokenManager with test encryption key
- Circuit breaker reset helper
- Fresh SubmissionLedger and SagaOrchestrator per test
- PIIFilter instance
- ConnectorHealthMonitor instance with reset CIRCUITS
"""

from __future__ import annotations

import os
import time

import pytest
from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# Encryption key — set BEFORE any token_store import so the module-level
# fallback branch picks it up.
# ---------------------------------------------------------------------------
_TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ["INTEGRATION_ENCRYPTION_KEY"] = _TEST_FERNET_KEY


from hr_advisory.mcp_servers.base import ArborMCPServer, TenantContext
from hr_advisory.mcp_servers.auth.token_store import ExternalTokenManager
from hr_advisory.mcp_servers.health import ConnectorHealthMonitor
from hr_advisory.mcp_servers.idempotency import SubmissionLedger
from hr_advisory.mcp_servers.pii_filter import PIIFilter
from hr_advisory.mcp_servers.resilience import (
    CIRCUITS,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
)
from hr_advisory.mcp_servers.saga import SagaOrchestrator


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TENANT_A = "company_100"
TENANT_B = "company_200"
USER_A = "user_a"
USER_B = "user_b"


# ---------------------------------------------------------------------------
# Base MCP Server
# ---------------------------------------------------------------------------


@pytest.fixture()
def mcp_server() -> ArborMCPServer:
    """Fresh ArborMCPServer with two test tools registered."""
    server = ArborMCPServer(
        name="arbor-test-server",
        description="Test MCP server",
        version="0.0.1",
    )

    @server.tool("test_echo", description="Echo input back")
    async def echo_tool(ctx: TenantContext, message: str = "hello") -> dict:
        return {"echo": message, "company_id": ctx.company_id}

    @server.tool("test_fail", description="Always raises")
    async def fail_tool(ctx: TenantContext) -> dict:
        raise RuntimeError("deliberate failure")

    @server.tool(
        "test_confirm",
        description="Requires confirmation",
        requires_confirmation=True,
    )
    async def confirm_tool(ctx: TenantContext) -> dict:
        return {"confirmed": True}

    return server


# ---------------------------------------------------------------------------
# Tenant contexts
# ---------------------------------------------------------------------------


@pytest.fixture()
def tenant_ctx_a() -> TenantContext:
    return TenantContext(company_id=TENANT_A, user_id=USER_A, role="admin")


@pytest.fixture()
def tenant_ctx_b() -> TenantContext:
    return TenantContext(company_id=TENANT_B, user_id=USER_B, role="admin")


# ---------------------------------------------------------------------------
# Token store
# ---------------------------------------------------------------------------


@pytest.fixture()
def token_manager() -> ExternalTokenManager:
    """Fresh ExternalTokenManager (no shared state between tests)."""
    return ExternalTokenManager()


@pytest.fixture()
def token_manager_with_tokens(token_manager: ExternalTokenManager) -> ExternalTokenManager:
    """Token manager pre-loaded with tokens for two tenants."""
    token_manager.store_token(
        TENANT_A,
        "xero",
        {
            "access_token": "xa_test_token_a",
            "refresh_token": "xr_test_refresh_a",
            "expires_in": 1800,
            "scope": "accounting.transactions accounting.contacts",
        },
    )
    token_manager.store_token(
        TENANT_B,
        "xero",
        {
            "access_token": "xa_test_token_b",
            "refresh_token": "xr_test_refresh_b",
            "expires_in": 1800,
            "scope": "accounting.transactions",
        },
    )
    token_manager.store_token(
        TENANT_A,
        "cpf_apex",
        {
            "access_token": "cpf_test_token",
            "expires_in": 3600,
        },
    )
    return token_manager


# ---------------------------------------------------------------------------
# Circuit breaker helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def circuit_breaker() -> CircuitBreaker:
    """Isolated circuit breaker with low thresholds for fast testing."""
    return CircuitBreaker(
        name="test_service",
        failure_threshold=3,
        recovery_timeout=1,  # 1 second for fast test turnaround
    )


@pytest.fixture(autouse=True)
def reset_global_circuits():
    """Reset all global CIRCUITS between tests to prevent state leakage."""
    original_states = {}
    for name, cb in CIRCUITS.items():
        original_states[name] = (cb._state, cb._failures, cb._total_calls, cb._total_failures)
    yield
    for name, cb in CIRCUITS.items():
        if name in original_states:
            state, failures, total_calls, total_failures = original_states[name]
            cb._state = state
            cb._failures = failures
            cb._total_calls = total_calls
            cb._total_failures = total_failures


@pytest.fixture()
def rate_limiter() -> RateLimiter:
    """Rate limiter with tight limits for testing."""
    return RateLimiter(max_calls=3, window_seconds=2)


# ---------------------------------------------------------------------------
# Idempotency ledger
# ---------------------------------------------------------------------------


@pytest.fixture()
def ledger() -> SubmissionLedger:
    """Fresh submission ledger per test."""
    return SubmissionLedger()


# ---------------------------------------------------------------------------
# Saga orchestrator
# ---------------------------------------------------------------------------


@pytest.fixture()
def orchestrator() -> SagaOrchestrator:
    """Fresh saga orchestrator per test."""
    return SagaOrchestrator()


# ---------------------------------------------------------------------------
# PII filter
# ---------------------------------------------------------------------------


@pytest.fixture()
def pii_filter() -> PIIFilter:
    return PIIFilter()


# ---------------------------------------------------------------------------
# Health monitor
# ---------------------------------------------------------------------------


@pytest.fixture()
def health_monitor() -> ConnectorHealthMonitor:
    """Fresh health monitor per test."""
    return ConnectorHealthMonitor()
