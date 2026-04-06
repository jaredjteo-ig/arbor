"""Integration management API router.

Exposes MCP server management, tool invocation, connector health,
submission ledger, saga status, and integration settings for the
admin dashboard and shadow agent.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.tenant_isolation import get_current_company_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request/Response Models ──────────────────────────────────


class ToolCallRequest(BaseModel):
    tool_name: str
    params: dict = {}


class ToolCallResponse(BaseModel):
    status: str
    result: dict = {}
    tool: str = ""


# ── MCP Server Discovery ────────────────────────────────────


@router.get("/servers")
async def list_servers(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all MCP integration servers and their status."""
    from hr_advisory.mcp_servers.registry import get_all_health

    return {"servers": get_all_health()}


@router.get("/tools")
async def list_tools(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all available MCP tools across all servers."""
    from hr_advisory.mcp_servers.registry import list_all_tools

    return {"tools": list_all_tools(), "count": len(list_all_tools())}


@router.get("/resources")
async def list_resources(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all available MCP resources."""
    from hr_advisory.mcp_servers.registry import list_all_resources

    return {"resources": list_all_resources()}


@router.post("/tools/call")
async def call_tool(
    request: ToolCallRequest,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Invoke an MCP tool. Used by the shadow agent for integration operations."""
    from hr_advisory.mcp_servers.registry import call_tool as mcp_call_tool

    company_id = str(get_current_company_id(current_user) or "")
    user_id = str(current_user.get("id", "unknown"))

    result = await mcp_call_tool(
        request.tool_name,
        company_id=company_id,
        user_id=user_id,
        **request.params,
    )
    return result


# ── Integration Status (frontend-facing) ────────────────────


@router.get("/status")
async def integration_status(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get connection status for all providers (frontend format).

    Maps the internal health monitor data to the ProviderStatus shape
    expected by the frontend integrations page.
    """
    from hr_advisory.mcp_servers.health import get_health_monitor

    monitor = get_health_monitor()
    statuses = monitor.get_all_statuses()

    # Map health status to connection status
    status_map = {
        "healthy": "disconnected",  # healthy infra but no credentials = not connected
        "degraded": "error",
        "down": "error",
        "unknown": "disconnected",
    }

    providers = []
    for connector in statuses:
        name = connector.get("name", connector.get("connector_id", "unknown"))
        health = connector.get("status", "unknown")
        providers.append({
            "provider": name,
            "category": connector.get("category", "other"),
            "status": status_map.get(health, "disconnected"),
            "last_sync": connector.get("last_success"),
            "error_message": None,
        })

    return {"providers": providers}


# ── Connector Health ─────────────────────────────────────────


@router.get("/health")
async def connector_health(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get health status of all connectors."""
    from hr_advisory.mcp_servers.health import get_health_monitor

    monitor = get_health_monitor()
    return {
        "summary": monitor.get_summary(),
        "connectors": monitor.get_all_statuses(),
    }


@router.get("/health/{connector_name}")
async def connector_health_detail(
    connector_name: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get detailed health for a specific connector."""
    from hr_advisory.mcp_servers.health import get_health_monitor

    monitor = get_health_monitor()
    return monitor.get_status(connector_name)


# ── Submission Ledger ────────────────────────────────────────


@router.get("/submissions")
async def list_submissions(
    submission_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List external submission records (CPF, IR8A, bank payments, etc.)."""
    from hr_advisory.mcp_servers.idempotency import (
        get_submission_ledger,
        SubmissionType,
        SubmissionStatus,
    )

    company_id = str(get_current_company_id(current_user) or "")
    ledger = get_submission_ledger()

    st = SubmissionType(submission_type) if submission_type else None
    ss = SubmissionStatus(status) if status else None

    records = ledger.list_submissions(
        tenant_id=company_id,
        submission_type=st,
        status=ss,
        limit=limit,
    )

    return {
        "submissions": [
            {
                "id": r.id,
                "type": r.submission_type.value,
                "period": r.period,
                "status": r.status.value,
                "external_reference": r.external_reference_id,
                "amount": r.amount,
                "employee_count": r.employee_count,
                "error": r.error_detail,
                "created_at": r.created_at.isoformat(),
                "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
            }
            for r in records
        ],
        "count": len(records),
    }


@router.post("/submissions/{record_id}/cancel")
async def cancel_submission(
    record_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Cancel a pending submission."""
    from hr_advisory.mcp_servers.idempotency import get_submission_ledger

    company_id = str(get_current_company_id(current_user) or "")
    ledger = get_submission_ledger()

    # Tenant isolation: verify the submission belongs to this company
    record = ledger.get_submission(record_id)
    if record is None or record.tenant_id != company_id:
        raise HTTPException(status_code=404, detail="Submission not found")

    try:
        ledger.cancel(record_id)
        return {"status": "cancelled", "id": record_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Saga Status ──────────────────────────────────────────────


@router.get("/sagas")
async def list_sagas(
    status: Optional[str] = None,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List multi-step operation sagas."""
    from hr_advisory.mcp_servers.saga import get_saga_orchestrator, SagaStatus

    company_id = str(get_current_company_id(current_user) or "")
    orchestrator = get_saga_orchestrator()

    ss = SagaStatus(status) if status else None
    sagas = orchestrator.list_sagas(tenant_id=company_id, status=ss, limit=limit)

    return {
        "sagas": [s.to_dict() for s in sagas],
        "count": len(sagas),
    }


@router.get("/sagas/{saga_id}")
async def get_saga_detail(
    saga_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get detailed saga execution status with step-by-step progress."""
    from hr_advisory.mcp_servers.saga import get_saga_orchestrator

    orchestrator = get_saga_orchestrator()
    saga = orchestrator.get_saga(saga_id)
    if saga is None:
        raise HTTPException(status_code=404, detail="Saga not found")

    company_id = get_current_company_id(current_user)
    if saga.tenant_id != company_id:
        raise HTTPException(status_code=404, detail="Saga not found")

    return saga.to_dict()


@router.post("/sagas/{saga_id}/resume")
async def resume_saga(
    saga_id: str,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Resume a failed saga from its last successful step."""
    from hr_advisory.mcp_servers.saga import get_saga_orchestrator

    company_id = str(get_current_company_id(current_user) or "")
    orchestrator = get_saga_orchestrator()

    # Tenant isolation: verify the saga belongs to this company
    existing = orchestrator.get_saga(saga_id)
    if existing is None or existing.tenant_id != company_id:
        raise HTTPException(status_code=404, detail="Saga not found")

    try:
        saga = orchestrator.resume_saga(saga_id)
        return saga.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Audit Log ────────────────────────────────────────────────


@router.get("/audit-log")
async def get_audit_log(
    tool_name: Optional[str] = None,
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get MCP tool invocation audit log."""
    from hr_advisory.mcp_servers.registry import get_all_servers

    company_id = get_current_company_id(current_user)
    all_entries = []

    for server in get_all_servers().values():
        entries = server.get_audit_log(company_id=company_id, limit=limit)
        if tool_name:
            entries = [e for e in entries if e["tool_name"] == tool_name]
        all_entries.extend(entries)

    all_entries.sort(key=lambda e: e["timestamp"], reverse=True)
    return {"entries": all_entries[:limit], "count": len(all_entries[:limit])}


# ── Connection Management ────────────────────────────────────


@router.get("/connections")
async def list_connections(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all active integration connections for the current company."""
    from hr_advisory.mcp_servers.auth.token_store import get_token_manager

    company_id = str(get_current_company_id(current_user) or "")
    manager = get_token_manager()
    return {"connections": manager.list_connections(company_id)}


@router.delete("/connections/{provider}")
async def disconnect_provider(
    provider: str,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Disconnect an integration provider (revoke OAuth token)."""
    from hr_advisory.mcp_servers.auth.token_store import get_token_manager

    company_id = str(get_current_company_id(current_user) or "")
    manager = get_token_manager()
    revoked = manager.revoke_token(company_id, provider)

    if not revoked:
        raise HTTPException(status_code=404, detail=f"No connection found for {provider}")

    return {"status": "disconnected", "provider": provider}


# ── Circuit Breakers (Admin) ─────────────────────────────────


@router.get("/circuits")
async def list_circuit_breakers(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all circuit breaker statuses (admin view)."""
    from hr_advisory.mcp_servers.resilience import get_all_circuit_statuses

    return {"circuits": get_all_circuit_statuses()}


@router.post("/circuits/{name}/reset")
async def reset_circuit_breaker(
    name: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Manually reset a circuit breaker (admin-only action)."""
    from hr_advisory.mcp_servers.resilience import get_circuit

    # Only owners and platform admins can reset circuit breakers
    role = current_user.get("role", "")
    if role not in ("owner", "platform_admin", "hr_manager"):
        raise HTTPException(status_code=403, detail="Admin role required to reset circuit breakers")

    circuit = get_circuit(name)
    circuit.reset()
    return {"status": "reset", "circuit": name}


# ── Webhook Endpoints ──────────────────────────────────────


# Simple per-IP rate limiter for unauthenticated webhook endpoint.
# Bounded to prevent memory exhaustion from spoofed IPs.
_webhook_rate: OrderedDict[str, list[float]] = OrderedDict()
_WEBHOOK_MAX_PER_MINUTE = 100
_WEBHOOK_MAX_KEYS = 50_000


def _check_webhook_rate(client_ip: str) -> bool:
    """Return True if allowed, False if rate limited."""
    import time

    now = time.monotonic()
    cutoff = now - 60
    calls = [t for t in _webhook_rate.get(client_ip, []) if t > cutoff]
    if len(calls) >= _WEBHOOK_MAX_PER_MINUTE:
        return False

    # Evict oldest entries if at capacity
    while len(_webhook_rate) >= _WEBHOOK_MAX_KEYS:
        _webhook_rate.popitem(last=False)

    calls.append(now)
    _webhook_rate[client_ip] = calls
    _webhook_rate.move_to_end(client_ip)
    return True


@router.post("/webhooks/{provider}")
async def receive_webhook(provider: str, request: Request) -> dict:
    """Receive inbound webhook from external service.

    Routes to the appropriate webhook handler after signature verification.
    Rate limited to 100 requests/minute per IP.
    """
    from hr_advisory.mcp_servers.webhooks import get_webhook_router

    # Rate limit by client IP
    client_ip = request.client.host if request.client else "unknown"
    if not _check_webhook_rate(client_ip):
        raise HTTPException(status_code=429, detail="Too many webhook requests")

    body = await request.body()
    headers = dict(request.headers)
    router_instance = get_webhook_router()
    return await router_instance.process_webhook(provider, headers, body)


# ── Cost Tracking Endpoints ────────────────────────────────


@router.get("/costs")
async def get_costs(current_user: dict = Depends(get_current_user)) -> dict:
    """Get per-tenant API cost breakdown for current month."""
    from hr_advisory.mcp_servers.cost_tracker import get_cost_tracker

    company_id = str(get_current_company_id(current_user) or "")
    tracker = get_cost_tracker()
    return tracker.get_monthly_cost(company_id)


@router.get("/costs/ceiling")
async def check_cost_ceiling(current_user: dict = Depends(get_current_user)) -> dict:
    """Check if tenant is approaching cost ceiling."""
    from hr_advisory.mcp_servers.cost_tracker import get_cost_tracker

    company_id = str(get_current_company_id(current_user) or "")
    tracker = get_cost_tracker()
    return tracker.check_cost_ceiling(company_id)


# ── Approval Endpoints (confirm_action gate) ──────────────


@router.get("/approvals")
async def list_pending_approvals(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """List all pending approval requests for the current company."""
    from hr_advisory.mcp_servers.confirm_action import get_approval_store

    company_id = str(get_current_company_id(current_user) or "")
    store = get_approval_store()
    pending = store.list_pending(company_id)
    return {"approvals": pending, "count": len(pending)}


@router.get("/approvals/{approval_id}")
async def get_approval_status(
    approval_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Check the status of a specific approval request."""
    from hr_advisory.mcp_servers.confirm_action import get_approval_store

    store = get_approval_store()
    result = store.check_approval(approval_id)

    # Tenant isolation: verify the approval belongs to this company
    company_id = str(get_current_company_id(current_user) or "")
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail="Approval not found")
    if result.get("tenant_id") and result["tenant_id"] != company_id:
        raise HTTPException(status_code=404, detail="Approval not found")

    return result


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Approve a pending action (human-in-the-loop confirmation).

    Called by the UI when a user clicks Approve on the confirmation modal.
    Only pending approvals belonging to the current company can be approved.
    """
    from hr_advisory.mcp_servers.confirm_action import get_approval_store

    company_id = str(get_current_company_id(current_user) or "")
    user_id = str(current_user.get("id", "unknown"))

    store = get_approval_store()

    # Tenant isolation check
    status = store.check_approval(approval_id)
    if status.get("status") == "error":
        raise HTTPException(status_code=404, detail="Approval not found")
    if status.get("tenant_id") and status["tenant_id"] != company_id:
        raise HTTPException(status_code=404, detail="Approval not found")

    result = store.approve(approval_id, decided_by=user_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    reason: str = "",
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Reject a pending action (human-in-the-loop denial).

    Called by the UI when a user clicks Reject on the confirmation modal.
    Only pending approvals belonging to the current company can be rejected.
    """
    from hr_advisory.mcp_servers.confirm_action import get_approval_store

    company_id = str(get_current_company_id(current_user) or "")
    user_id = str(current_user.get("id", "unknown"))

    store = get_approval_store()

    # Tenant isolation check
    status = store.check_approval(approval_id)
    if status.get("status") == "error":
        raise HTTPException(status_code=404, detail="Approval not found")
    if status.get("tenant_id") and status["tenant_id"] != company_id:
        raise HTTPException(status_code=404, detail="Approval not found")

    result = store.reject(approval_id, reason=reason, decided_by=user_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# ── Accounting Sync ─────────────────────────────────────────


@router.get("/accounting-sync")
async def accounting_sync_status(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get accounting sync status for payroll runs.

    Returns sync records showing which payroll runs have been synced
    to the configured accounting provider (Xero, QuickBooks, Zoho).
    Returns an empty list if no accounting provider is configured.
    """
    company_id = str(get_current_company_id(current_user) or "")

    # Try to get sync records from the accounting server if available
    try:
        from hr_advisory.mcp_servers.registry import get_server
        server = get_server("accounting")
        if server is not None:
            records = server.get_sync_records(company_id=company_id)
            return {"records": records, "total": len(records)}
    except Exception:
        logger.debug("Accounting server not available, returning empty sync status")

    return {
        "records": [],
        "total": 0,
    }


@router.post("/accounting-sync/{run_id}")
async def trigger_accounting_sync(
    run_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Trigger accounting sync for a specific payroll run.

    Initiates a journal entry push to the configured accounting provider.
    Returns an error if no accounting provider is configured.
    """
    company_id = str(get_current_company_id(current_user) or "")

    try:
        from hr_advisory.mcp_servers.registry import call_tool as mcp_call_tool
        result = await mcp_call_tool(
            "accounting_sync_payroll",
            company_id=company_id,
            user_id=str(current_user.get("id", "unknown")),
            run_id=run_id,
        )
        return result
    except Exception as exc:
        logger.warning("Accounting sync failed for run_id=%s: %s", run_id, exc)
        raise HTTPException(
            status_code=400,
            detail="Accounting sync is not configured. Connect an accounting provider in Integrations settings.",
        )


# ── SkillsFuture Courses ───────────────────────────────────


@router.get("/skillsfuture/courses")
async def list_skillsfuture_courses(
    query: Optional[str] = None,
    topic: Optional[str] = None,
    duration: Optional[str] = None,
    funding: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Search SkillsFuture courses.

    Returns courses from the SkillsFuture Singapore API.
    Returns an empty list if SkillsFuture API credentials are not configured.
    """
    # Try to call the SkillsFuture MCP tool if available
    try:
        from hr_advisory.mcp_servers.registry import call_tool as mcp_call_tool
        company_id = str(get_current_company_id(current_user) or "")
        params = {}
        if query:
            params["query"] = query
        if topic:
            params["topic"] = topic
        if duration:
            params["duration"] = duration
        if funding:
            params["funding"] = funding

        result = await mcp_call_tool(
            "skillsfuture_search_courses",
            company_id=company_id,
            user_id=str(current_user.get("id", "unknown")),
            **params,
        )
        return result
    except Exception:
        logger.debug("SkillsFuture MCP tool not available")

    return {
        "courses": [],
        "total": 0,
    }


@router.get("/skillsfuture/courses/{course_id}/grant-check")
async def check_skillsfuture_grant(
    course_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Check SkillsFuture grant eligibility for a specific course.

    Returns eligibility info or a default response if the API is not configured.
    """
    try:
        from hr_advisory.mcp_servers.registry import call_tool as mcp_call_tool
        company_id = str(get_current_company_id(current_user) or "")
        result = await mcp_call_tool(
            "skillsfuture_check_grant",
            company_id=company_id,
            user_id=str(current_user.get("id", "unknown")),
            course_id=course_id,
        )
        return result
    except Exception:
        logger.debug("SkillsFuture grant check not available")

    return {
        "eligible": False,
        "grant_amount": 0,
        "sfc_balance": 0,
        "message": "SkillsFuture API credentials are not configured. Connect SkillsFuture in Integrations settings.",
    }
