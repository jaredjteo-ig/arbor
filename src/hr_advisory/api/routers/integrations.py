"""Integration management API router.

Exposes MCP server management, tool invocation, connector health,
submission ledger, saga status, and integration settings for the
admin dashboard and shadow agent.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from hr_advisory.api.middleware.auth_middleware import get_current_user
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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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
    current_user: dict = Depends(get_current_user),
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


# Simple per-IP rate limiter for unauthenticated webhook endpoint
_webhook_rate: dict[str, list[float]] = {}
_WEBHOOK_MAX_PER_MINUTE = 100


def _check_webhook_rate(client_ip: str) -> bool:
    """Return True if allowed, False if rate limited."""
    import time

    now = time.monotonic()
    cutoff = now - 60
    calls = [t for t in _webhook_rate.get(client_ip, []) if t > cutoff]
    if len(calls) >= _WEBHOOK_MAX_PER_MINUTE:
        return False
    calls.append(now)
    _webhook_rate[client_ip] = calls
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
    current_user: dict = Depends(get_current_user),
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
