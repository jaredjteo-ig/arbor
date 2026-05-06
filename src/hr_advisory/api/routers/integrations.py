"""Integration management API router.

Exposes MCP server management, tool invocation, connector health,
submission ledger, saga status, and integration settings for the
admin dashboard and shadow agent.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
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
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"call_tool:{user_id}", max_requests=30, window_seconds=60, action_name="call integration tool")

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
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Cancel a pending submission."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"cancel_submission:{user_id}", max_requests=30, window_seconds=60, action_name="cancel submission")

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
        logger.error("Failed to cancel submission %s: %s", record_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to cancel this submission."
        ) from e


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
    if str(saga.tenant_id) != str(company_id):
        raise HTTPException(status_code=404, detail="Saga not found")

    return saga.to_dict()


@router.post("/sagas/{saga_id}/resume")
async def resume_saga(
    saga_id: str,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Resume a failed saga from its last successful step."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"resume_saga:{user_id}", max_requests=30, window_seconds=60, action_name="resume saga")

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
        logger.error("Failed to resume saga %s: %s", saga_id, e)
        raise HTTPException(
            status_code=400, detail="Unable to resume this operation."
        ) from e


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
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"disconnect_provider:{user_id}", max_requests=30, window_seconds=60, action_name="disconnect provider")

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
    current_user: dict = Depends(require_role("owner")),
) -> dict:
    """Manually reset a circuit breaker (admin-only action)."""
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"reset_circuit:{user_id}", max_requests=30, window_seconds=60, action_name="reset circuit breaker")

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
    rl_user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"approve_action:{rl_user_id}", max_requests=30, window_seconds=60, action_name="approve action")

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
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Reject a pending action (human-in-the-loop denial).

    Called by the UI when a user clicks Reject on the confirmation modal.
    Only pending approvals belonging to the current company can be rejected.
    """
    rl_user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"reject_action:{rl_user_id}", max_requests=30, window_seconds=60, action_name="reject action")

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
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"accounting_sync:{user_id}", max_requests=30, window_seconds=60, action_name="trigger accounting sync")

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


_FALLBACK_SKILLSFUTURE_COURSES = [
    {
        "id": "WSQ-DAA-2026",
        "title": "Workforce Skills — Data Analytics for Business",
        "provider": "NTUC LearningHub",
        "duration_hours": 40,
        "funding": "SkillsFuture Credit eligible (up to $500)",
        "topics": ["data", "analytics", "business"],
    },
    {
        "id": "WSH-SSS-2026",
        "title": "WSH Site Safety Supervisor Course",
        "provider": "Singapore Polytechnic",
        "duration_hours": 16,
        "funding": "Up to 90% subsidy for SMEs",
        "topics": ["wsh", "compliance", "safety"],
    },
    {
        "id": "EW-CMS-2026",
        "title": "Effective Workplace Communication",
        "provider": "NTUC LearningHub",
        "duration_hours": 8,
        "funding": "SkillsFuture Credit eligible",
        "topics": ["communication", "soft-skills"],
    },
    {
        "id": "SG-EA-2026",
        "title": "Singapore Employment Act Foundations (HR)",
        "provider": "SHRI",
        "duration_hours": 12,
        "funding": "SkillsFuture Credit eligible",
        "topics": ["hr", "compliance", "law"],
    },
    {
        "id": "PM-AGILE-2026",
        "title": "Agile Project Management for SG SMEs",
        "provider": "Singapore Management University",
        "duration_hours": 24,
        "funding": "SkillsFuture Credit eligible (up to $500)",
        "topics": ["project-management", "agile"],
    },
    {
        "id": "DIG-MARK-2026",
        "title": "Digital Marketing Essentials",
        "provider": "Republic Polytechnic",
        "duration_hours": 16,
        "funding": "Up to 70% subsidy",
        "topics": ["marketing", "digital"],
    },
    {
        "id": "FIN-LITER-2026",
        "title": "Financial Literacy for SME Owners",
        "provider": "NTUC LearningHub",
        "duration_hours": 12,
        "funding": "SkillsFuture Credit eligible",
        "topics": ["finance", "leadership"],
    },
]


def _is_mcp_failure(result: dict | None) -> bool:
    """Detect MCP tool-not-found / error responses so we can fall back."""
    if not isinstance(result, dict):
        return True
    if result.get("status") == "error":
        return True
    if "courses" not in result and "error" in result:
        return True
    return False


@router.get("/skillsfuture/courses")
async def list_skillsfuture_courses(
    query: Optional[str] = None,
    topic: Optional[str] = None,
    duration: Optional[str] = None,
    funding: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Search SkillsFuture courses.

    Falls back to a curated catalogue (round-12 redteam B2) when the
    SkillsFuture MCP tool is not available — otherwise the L&D card on
    the Lifecycle Dashboard would dead-end on an error message rather
    than show learners options.
    """
    try:
        from hr_advisory.mcp_servers.registry import call_tool as mcp_call_tool
        company_id = str(get_current_company_id(current_user) or "")
        params: dict[str, Any] = {}
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
        if not _is_mcp_failure(result):
            return result
        logger.debug("SkillsFuture MCP returned an error payload — falling back to curated catalogue.")
    except Exception:
        logger.debug("SkillsFuture MCP tool not available — falling back to curated catalogue.")

    # Curated fallback. Filter by query/topic/duration so the UX feels live.
    rows = list(_FALLBACK_SKILLSFUTURE_COURSES)
    if query:
        q = query.lower()
        rows = [
            r
            for r in rows
            if q in r["title"].lower()
            or q in r["provider"].lower()
            or any(q in t for t in r["topics"])
        ]
    if topic:
        t = topic.lower()
        rows = [r for r in rows if t in r["topics"]]
    if duration:
        try:
            cap = int(duration)
            rows = [r for r in rows if r["duration_hours"] <= cap]
        except ValueError:
            pass
    return {
        "courses": rows,
        "total": len(rows),
        "source": "curated-fallback",
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


# ── Import Preview / Confirm ─────────────────────────────────
# IMPORTANT: These literal-path routes MUST be registered before the
# /{provider}/... parameterized routes below, otherwise FastAPI will
# try to match "import" as a {provider} path parameter.


class ImportPreviewRequest(BaseModel):
    source: str  # "talenox" | "hreasily" | "csv"
    data: Optional[dict] = None


class ImportConfirmRequest(BaseModel):
    source: str
    field_mappings: list[dict] = []


@router.post("/import/preview")
async def import_preview(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Preview employee data import.

    Accepts either a JSON body with {source, data} or multipart form data
    with a file upload. Returns field mappings, validation errors, and a
    preview of the first few rows.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"import_preview:{user_id}", max_requests=30, window_seconds=60, action_name="preview import")

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    content_type = request.headers.get("content-type", "")

    source = "csv"
    raw_rows: list[dict] = []

    if "multipart/form-data" in content_type:
        # Handle file upload
        form = await request.form()
        source = str(form.get("source", "csv"))
        upload = form.get("file")
        if upload is not None:
            import csv
            import io

            content = await upload.read()
            if len(content) > 5_000_000:
                raise HTTPException(status_code=413, detail="File too large. Maximum 5MB.")
            text = content.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                raw_rows.append(dict(row))
                if len(raw_rows) > 10_000:
                    raise HTTPException(status_code=400, detail="Too many rows. Maximum 10,000.")
    else:
        body = await request.json()
        source = body.get("source", "csv")
        raw_rows = body.get("data", [])
        if isinstance(raw_rows, dict):
            raw_rows = [raw_rows]

    # Determine field mappings from first row
    target_fields = [
        "employee_id_internal", "department", "designation", "employment_type",
        "start_date", "end_date", "nationality", "salary_monthly", "date_of_birth",
        "gender", "nric_fin", "bank_name", "bank_account_number",
    ]
    field_mappings = []
    if raw_rows:
        first_row = raw_rows[0]
        for source_field in first_row:
            # Auto-map if the source field name matches a target field
            normalised = source_field.lower().replace(" ", "_").replace("-", "_")
            mapped_to = normalised if normalised in target_fields else ""
            field_mappings.append({
                "source_field": source_field,
                "target_field": mapped_to,
                "sample_value": str(first_row.get(source_field, ""))[:100],
                "is_mapped": bool(mapped_to),
            })

    # Validate rows
    validation_errors = []
    valid_count = 0
    for idx, row in enumerate(raw_rows):
        row_errors = []
        # Check for required fields based on mappings
        if not any(v for v in row.values()):
            row_errors.append({"row": idx + 1, "field": "*", "message": "Empty row"})
        if row_errors:
            validation_errors.extend(row_errors)
        else:
            valid_count += 1

    # Check for duplicates based on employee_id_internal or NRIC
    seen_ids: set[str] = set()
    duplicate_count = 0
    for row in raw_rows:
        eid = str(row.get("employee_id_internal", row.get("Employee ID", "")))
        if eid and eid in seen_ids:
            duplicate_count += 1
        elif eid:
            seen_ids.add(eid)

    return {
        "source": source,
        "total_records": len(raw_rows),
        "valid_records": valid_count,
        "duplicate_count": duplicate_count,
        "field_mappings": field_mappings,
        "validation_errors": validation_errors[:50],  # Cap error list
        "preview_rows": [
            {k: str(v)[:100] for k, v in row.items()} for row in raw_rows[:10]
        ],
    }


@router.post("/import/confirm")
async def import_confirm(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Confirm and execute employee data import.

    Accepts {source, field_mappings} and creates Employee records
    for each valid row using the provided field mappings.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"import_confirm:{user_id}", max_requests=30, window_seconds=60, action_name="confirm import")

    from hr_advisory.services import dataflow_crud

    company_id = get_current_company_id(current_user)
    if company_id is None:
        raise HTTPException(status_code=400, detail="No company associated.")

    body = await request.json()
    source = body.get("source", "csv")
    field_mappings = body.get("field_mappings", [])
    rows = body.get("data", [])

    if not field_mappings:
        raise HTTPException(status_code=400, detail="field_mappings is required.")
    if len(rows) > 10_000:
        raise HTTPException(status_code=400, detail="Too many rows. Maximum 10,000.")

    # Build mapping dict: source_field -> target_field
    mapping = {}
    for fm in field_mappings:
        if fm.get("is_mapped") and fm.get("target_field"):
            mapping[fm["source_field"]] = fm["target_field"]

    imported = 0
    skipped = 0
    errors = 0

    for row in rows:
        try:
            record = {"company_id": company_id, "is_active": True}
            for src_field, tgt_field in mapping.items():
                if src_field in row:
                    record[tgt_field] = row[src_field]

            # Skip rows with no meaningful data
            if len(record) <= 2:  # only company_id and is_active
                skipped += 1
                continue

            dataflow_crud.create("Employee", record)
            imported += 1
        except Exception as exc:
            logger.warning("Import row error: %s", exc)
            errors += 1

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "message": f"Imported {imported} employees from {source}. {skipped} skipped, {errors} errors.",
    }


# ── Provider Connect / Disconnect / Test ──────────────────────
# IMPORTANT: These /{provider}/... parameterized routes MUST come AFTER
# all literal-path routes (like /import/preview) to avoid FastAPI matching
# literal segments as the {provider} parameter.


# In-memory connection store keyed by (company_id, provider).
# Bounded to prevent unbounded memory growth.
_MAX_CONNECTIONS = 10_000
_connection_store: OrderedDict[str, dict] = OrderedDict()


def _connection_key(company_id: str, provider: str) -> str:
    return f"{company_id}:{provider}"


def _store_connection(company_id: str, provider: str, config: dict) -> None:
    """Store a provider connection, evicting oldest if at capacity."""
    import time

    key = _connection_key(company_id, provider)
    while len(_connection_store) >= _MAX_CONNECTIONS and key not in _connection_store:
        _connection_store.popitem(last=False)
    _connection_store[key] = {
        "provider": provider,
        "company_id": company_id,
        "config": config,
        "status": "connected",
        "connected_at": time.time(),
    }
    _connection_store.move_to_end(key)


def _remove_connection(company_id: str, provider: str) -> bool:
    """Remove a provider connection. Returns True if it existed."""
    key = _connection_key(company_id, provider)
    if key in _connection_store:
        del _connection_store[key]
        return True
    return False


def _get_connection(company_id: str, provider: str) -> dict | None:
    """Look up a stored connection."""
    return _connection_store.get(_connection_key(company_id, provider))


@router.post("/{provider}/connect")
async def connect_provider(
    provider: str,
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Connect a provider (OAuth or API key setup).

    Accepts optional configuration in the request body (api_key, endpoint_url).
    Returns a redirect_url for OAuth providers or a success status for API key providers.
    """
    import re

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"connect_provider:{user_id}", max_requests=30, window_seconds=60, action_name="connect provider")

    # Validate provider name to prevent injection
    if not re.match(r"^[a-zA-Z0-9_-]+$", provider):
        raise HTTPException(status_code=400, detail="Invalid provider name.")

    company_id = str(get_current_company_id(current_user) or "")

    # Parse optional body — may be empty for OAuth flows
    try:
        body = await request.json()
    except Exception:
        body = {}

    config = {
        "api_key": body.get("api_key", ""),
        "endpoint_url": body.get("endpoint_url", ""),
    }

    _store_connection(company_id, provider, config)

    logger.info("Provider %s connected for company %s", provider, company_id)

    # For OAuth providers we would return a redirect URL; for API key providers
    # we confirm success immediately. Since we don't have real OAuth wired up,
    # return a status-only response that the frontend can handle.
    return {"redirect_url": "", "status": "connected", "provider": provider}


@router.post("/{provider}/disconnect")
async def disconnect_provider_post(
    provider: str,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Disconnect a provider (POST variant matching frontend expectation).

    Also attempts to revoke the OAuth token if a token-based connection exists.
    """
    import re

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"disconnect_provider_post:{user_id}", max_requests=30, window_seconds=60, action_name="disconnect provider")

    if not re.match(r"^[a-zA-Z0-9_-]+$", provider):
        raise HTTPException(status_code=400, detail="Invalid provider name.")

    # Round-13 H: certain providers have dedicated disconnect handlers that
    # perform real OAuth-token revocation and delete persisted connection
    # rows (e.g. ``GoogleCalendarConnection``). FastAPI matches routes in
    # registration order, and the generic ``/{provider}/disconnect`` route
    # below is registered BEFORE provider-specific routers — so without
    # this guard the generic handler shadows the dedicated one and returns
    # a fake-success response without revoking anything.
    #
    # We refuse the request here so the dedicated route is the only way to
    # disconnect these providers. The dedicated route lives at
    # ``POST /integrations/google-calendar/disconnect`` (see
    # ``integrations_calendar.py``). The 404 surfaces clearly in logs if
    # router registration order ever regresses.
    _DEDICATED_DISCONNECT_PROVIDERS = {"google-calendar"}
    if provider in _DEDICATED_DISCONNECT_PROVIDERS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Generic disconnect is not supported for '{provider}'. "
                f"Use the dedicated /integrations/{provider}/disconnect route."
            ),
        )

    company_id = str(get_current_company_id(current_user) or "")

    # Remove from in-memory store
    removed = _remove_connection(company_id, provider)

    # Also try the token manager (existing DELETE endpoint logic)
    try:
        from hr_advisory.mcp_servers.auth.token_store import get_token_manager

        manager = get_token_manager()
        manager.revoke_token(company_id, provider)
    except Exception:
        pass  # Token manager may not be configured; in-memory removal is sufficient

    if not removed:
        # Check if there was a token-based connection
        logger.debug("No in-memory connection for %s/%s, may have been token-only", provider, company_id)

    return {"message": f"Disconnected from {provider}.", "provider": provider}


@router.post("/{provider}/test")
async def test_provider_connection(
    provider: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Test a provider connection with a health check.

    Returns provider name, success status, message, and latency.
    """
    import re
    import time

    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"test_provider:{user_id}", max_requests=30, window_seconds=60, action_name="test provider connection")

    if not re.match(r"^[a-zA-Z0-9_-]+$", provider):
        raise HTTPException(status_code=400, detail="Invalid provider name.")

    company_id = str(get_current_company_id(current_user) or "")
    start_time = time.monotonic()

    # Check if a connection exists (in-memory or via health monitor)
    conn = _get_connection(company_id, provider)

    # Also check the health monitor for MCP-based connectors
    try:
        from hr_advisory.mcp_servers.health import get_health_monitor

        monitor = get_health_monitor()
        health = monitor.get_status(provider)
        health_status = health.get("status", "unknown")
    except Exception:
        health_status = "unknown"

    elapsed_ms = round((time.monotonic() - start_time) * 1000, 1)

    if conn is not None:
        return {
            "provider": provider,
            "success": True,
            "message": f"Connection to {provider} is active.",
            "latency_ms": elapsed_ms,
        }

    if health_status in ("healthy",):
        return {
            "provider": provider,
            "success": True,
            "message": f"Connector {provider} is healthy.",
            "latency_ms": elapsed_ms,
        }

    return {
        "provider": provider,
        "success": False,
        "message": f"No active connection found for {provider}. Please connect first.",
        "latency_ms": elapsed_ms,
    }
