"""Alerts API router — user-facing regulatory alert notifications.

Exposes published regulatory updates as alerts for end users (non-admin).
Tracks per-user read/dismissed status separately from the admin update workflow.
"""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from hr_advisory.api.middleware.auth_middleware import get_current_user, require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.workflows.regulatory_updates import (
    RegulatoryUpdate,
    UpdateStatus,
    UpdateUrgency,
    _updates,
    list_updates,
)
from pydantic import BaseModel


router = APIRouter(tags=["alerts"])

# ── Per-user alert status tracking ────────────────────────────
# Maps (user_id, alert_id) -> status. In production this would be a database.
_MAX_ALERT_STATUS_ENTRIES = 10000

_alert_status: OrderedDict[tuple[str, str], str] = OrderedDict()

# ── Dynamic alerts store ────────────────────────────────────
# Escalation alerts and other dynamic alerts are pushed here at runtime.
# Bounded to prevent OOM — oldest alerts evicted when over limit.
_MAX_DYNAMIC_ALERTS = 100
_alerts_store: list[dict] = []

# ── Seed data ────────────────────────────────────────────────
# Pre-populate with published regulatory updates so users see alerts
# immediately. In production, alerts are created when updates are published.

_SEED_ALERTS: list[dict] = [
    {
        "id": "alert-001",
        "title": "Progressive Wage Model extended to food services sector",
        "description": (
            "The Ministry of Manpower has gazetted the extension of the Progressive Wage Model (PWM) "
            "to cover all food services employees. Employers in the food services sector must comply "
            "with the new minimum wage ladder and training requirements."
        ),
        "source": "MOM",
        "urgency": "critical",
        "effective_date": "2026-03-01",
        "created_at": "2026-03-01T09:00:00Z",
        "domains_affected": ["Wages & PWM"],
        "impact_summary": (
            "If your company operates in food services or has employees classified under this sector, "
            "you must implement the new PWM wage ladder immediately. Non-compliance can result in "
            "restrictions on work pass approvals and renewals."
        ),
        "actions": [
            "Review all food services employee salaries against the new PWM wage ladder.",
            "Adjust salaries for any employees falling below the new minimums before the effective date.",
            "Enrol affected employees in required PWM training programmes.",
            "Update payroll systems to reflect the new wage floor.",
        ],
    },
    {
        "id": "alert-002",
        "title": "Updated CPF contribution rates for 2026",
        "description": (
            "CPF Board has published the updated CPF contribution rate tables for 2026, reflecting "
            "the next phase of increases for senior workers aged 55 to 70 as part of the scheduled step-up plan."
        ),
        "source": "CPF Board",
        "urgency": "high",
        "effective_date": "2026-02-15",
        "created_at": "2026-02-15T08:00:00Z",
        "domains_affected": ["CPF"],
        "impact_summary": (
            "If you employ workers aged 55 and above, your employer CPF contribution rates will increase. "
            "This affects your total employment cost. Payroll systems must be updated to reflect the new "
            "rates from 1 January 2026."
        ),
        "actions": [
            "Download the 2026 CPF contribution rate table from the CPF Board website.",
            "Update your payroll software with the new contribution rates.",
            "Recalculate total employment costs for affected employees.",
            "Notify affected employees about changes to their take-home pay.",
        ],
    },
    {
        "id": "alert-003",
        "title": "TG-FWAR updated guidelines on Flexible Work Arrangements",
        "description": (
            "The Tripartite Guidelines on Flexible Work Arrangement Requests (TG-FWAR) have been "
            "updated with new provisions clarifying employer response timelines and documentation "
            "requirements for FWA requests."
        ),
        "source": "TAFEP",
        "urgency": "medium",
        "effective_date": "2026-01-20",
        "created_at": "2026-01-20T10:00:00Z",
        "domains_affected": ["Fair Employment"],
        "impact_summary": (
            "All employers must now respond to FWA requests within 2 months with documented reasons "
            "if the request is rejected. Failure to comply may result in referral to TAFEP for investigation."
        ),
        "actions": [
            "Review your current FWA policy against the updated TG-FWAR guidelines.",
            "Update your FWA request form to capture newly required information.",
            "Train HR personnel and managers on the updated response timeline requirements.",
            "Implement a tracking system for FWA requests and responses.",
        ],
    },
    {
        "id": "alert-004",
        "title": "WICA insurance minimum coverage increase",
        "description": (
            "The Ministry of Manpower has increased the minimum Work Injury Compensation Act (WICA) "
            "insurance coverage amounts. Employers must ensure their work injury compensation insurance "
            "policies meet the new minimums."
        ),
        "source": "MOM",
        "urgency": "high",
        "effective_date": "2026-03-10",
        "created_at": "2026-03-10T07:30:00Z",
        "domains_affected": ["Workplace Safety"],
        "impact_summary": (
            "Your existing WICA insurance policy may no longer meet the new minimum coverage requirements. "
            "Insufficient coverage exposes your company to direct liability for work injury claims "
            "and potential prosecution."
        ),
        "actions": [
            "Check your current WICA insurance policy coverage limits against the new minimums.",
            "Contact your insurer to increase coverage if it falls below the new thresholds.",
            "Ensure all employees (including part-time and contract workers) are covered.",
            "Keep updated certificates of insurance accessible for MOM inspection.",
        ],
    },
    {
        "id": "alert-005",
        "title": "PDPA data breach notification deadline shortened",
        "description": (
            "The Personal Data Protection Commission (PDPC) has shortened the mandatory data breach "
            "notification deadline from 3 calendar days to 72 hours. Organisations must notify both the "
            "PDPC and affected individuals within the new timeframe."
        ),
        "source": "PDPC",
        "urgency": "critical",
        "effective_date": "2026-02-28",
        "created_at": "2026-02-28T14:00:00Z",
        "domains_affected": ["Data Protection"],
        "impact_summary": (
            "Your company's data breach response plan must be updated to meet the shorter 72-hour "
            "notification window. Late notifications can result in fines up to $1 million or 10% of "
            "annual turnover."
        ),
        "actions": [
            "Update your Data Breach Response Plan with the new 72-hour notification timeline.",
            "Designate a Data Protection Officer (DPO) if you have not already done so.",
            "Conduct a tabletop exercise to test your response plan against the new deadline.",
            "Pre-draft notification templates for both PDPC and affected individuals.",
        ],
    },
    {
        "id": "alert-006",
        "title": "Updated foreign worker levy rates for 2026",
        "description": (
            "MOM has revised the foreign worker levy rates for S Pass and Work Permit holders across "
            "multiple sectors, as part of the scheduled levy adjustments announced in Budget 2024."
        ),
        "source": "MOM",
        "urgency": "high",
        "effective_date": "2026-03-05",
        "created_at": "2026-03-05T11:00:00Z",
        "domains_affected": ["Foreign Manpower"],
        "impact_summary": (
            "If you employ foreign workers on S Pass or Work Permit, your monthly levy costs will change. "
            "This directly affects your total employment costs and may impact hiring decisions for "
            "new foreign hires."
        ),
        "actions": [
            "Review the updated levy rate schedule for your sector and pass type.",
            "Recalculate the total cost of employing each foreign worker.",
            "Update your budget forecasts to account for the new levy amounts.",
            "Consider whether headcount adjustments are needed based on the cost impact.",
        ],
    },
    {
        "id": "alert-007",
        "title": "New TAFEP guidelines on age discrimination in hiring",
        "description": (
            "TAFEP has published new guidelines strengthening protections against age discrimination "
            "in hiring. Job advertisements must not include age-related requirements unless there is "
            "a genuine occupational qualification."
        ),
        "source": "TAFEP",
        "urgency": "medium",
        "effective_date": "2026-01-15",
        "created_at": "2026-01-15T09:00:00Z",
        "domains_affected": ["Fair Employment"],
        "impact_summary": (
            "All job advertisements and hiring processes must be reviewed to remove age-related "
            "requirements. Non-compliance can lead to TAFEP investigation and restrictions on work "
            "pass privileges."
        ),
        "actions": [
            "Audit all current job postings for age-related language or requirements.",
            "Update your recruitment policy to align with the new TAFEP guidelines.",
            "Brief hiring managers on acceptable and non-acceptable selection criteria.",
            "Review interview question templates to remove age-biased questions.",
        ],
    },
    {
        "id": "alert-008",
        "title": "EA amendment: increased penalty for late salary payment",
        "description": (
            "The Employment Act has been amended to increase the maximum fine for late salary payment "
            "from $5,000 to $15,000 per offence, with the possibility of imprisonment for repeat offenders."
        ),
        "source": "MOM",
        "urgency": "critical",
        "effective_date": "2026-03-08",
        "created_at": "2026-03-08T08:30:00Z",
        "domains_affected": ["Employment Act"],
        "impact_summary": (
            "Late salary payment penalties have tripled. If your company has ever paid salaries late "
            "(beyond 7 days after the salary period), this significantly increases your financial risk. "
            "Repeat offences can now result in imprisonment."
        ),
        "actions": [
            "Ensure payroll runs are completed at least 2 business days before the statutory deadline.",
            "Set up automated payroll processing to prevent manual delays.",
            "Review and tighten your salary payment schedule with your bank.",
            "Implement a backup payment process for system failures or bank holidays.",
        ],
    },
]


def _get_seed_alerts(company_id: int | None = None) -> list[dict]:
    """Return seed alerts combined with any published regulatory updates.

    Seed alerts and published regulatory updates are system-wide (visible to all).
    Dynamic alerts (escalations) are filtered by company_id to prevent cross-tenant leaks.
    """
    alerts = list(_SEED_ALERTS)

    # Also include any dynamically published regulatory updates
    published = list_updates(UpdateStatus.PUBLISHED)
    existing_ids = {a["id"] for a in alerts}
    for update in published:
        if update.id not in existing_ids:
            alerts.append({
                "id": update.id,
                "title": update.title,
                "description": update.description,
                "source": update.source,
                "urgency": update.urgency.value,
                "effective_date": update.effective_date.isoformat(),
                "created_at": update.created_at.isoformat(),
                "domains_affected": update.domains_affected,
                "impact_summary": update.impact_summary,
                "actions": [],
            })

    # Include dynamic alerts (escalations, etc.) — filtered by company_id
    existing_ids = {a["id"] for a in alerts}
    for alert in _alerts_store:
        if alert["id"] not in existing_ids:
            # Only include alerts belonging to the requesting company
            alert_company = alert.get("company_id")
            if company_id is not None and alert_company is not None and alert_company != company_id:
                continue
            alerts.append(alert)

    # Evict oldest dynamic alerts if over limit
    while len(_alerts_store) > _MAX_DYNAMIC_ALERTS:
        _alerts_store.pop(0)

    return alerts


# ── Response models ──────────────────────────────────────────


class AlertResponse(BaseModel):
    id: str
    title: str
    description: str
    severity: str
    status: str
    domain: str
    created_at: str
    impact_summary: str
    actions: list[str]
    effective_date: str
    source: str


class AlertListResponse(BaseModel):
    alerts: list[AlertResponse]
    count: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


# ── Helpers ──────────────────────────────────────────────────


def _user_id_from_payload(user: dict) -> str:
    """Extract a stable user identifier from the JWT payload."""
    return str(user.get("sub", "anonymous"))


def _alert_status_for_user(user_id: str, alert_id: str) -> str:
    """Get the read/dismissed status for a specific user and alert."""
    return _alert_status.get((user_id, alert_id), "unread")


def _to_alert_response(alert_data: dict, user_id: str) -> AlertResponse:
    """Convert raw alert data + user status into an AlertResponse."""
    urgency = alert_data.get("urgency", "medium")
    # Map urgency to severity (they use the same scale)
    severity = urgency if urgency in ("critical", "high", "medium", "low") else "medium"
    domains = alert_data.get("domains_affected", [])
    domain = domains[0] if domains else "General"

    return AlertResponse(
        id=alert_data["id"],
        title=alert_data["title"],
        description=alert_data["description"],
        severity=severity,
        status=_alert_status_for_user(user_id, alert_data["id"]),
        domain=domain,
        created_at=alert_data.get("created_at", datetime.now(timezone.utc).isoformat()),
        impact_summary=alert_data.get("impact_summary", ""),
        actions=alert_data.get("actions", []),
        effective_date=alert_data.get("effective_date", ""),
        source=alert_data.get("source", ""),
    )


# ── Endpoints ────────────────────────────────────────────────


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    severity: str | None = None,
    status: str | None = None,
    current_user: dict = Depends(require_role("owner", "hr_manager", "consultant")),
) -> AlertListResponse:
    """List regulatory alerts for the current user.

    Optionally filter by severity (critical, high, medium, low)
    and status (unread, read, dismissed).
    """
    user_id = _user_id_from_payload(current_user)
    company_id = current_user.get("company_id")
    raw_alerts = _get_seed_alerts(company_id)

    responses = [_to_alert_response(a, user_id) for a in raw_alerts]

    # Apply filters
    if severity:
        responses = [a for a in responses if a.severity == severity]
    if status:
        responses = [a for a in responses if a.status == status]

    # Sort by date descending
    responses.sort(key=lambda a: a.created_at, reverse=True)

    unread_count = sum(
        1
        for a in _get_seed_alerts(company_id)
        if _alert_status_for_user(user_id, a["id"]) == "unread"
    )

    return AlertListResponse(
        alerts=responses,
        count=len(responses),
        unread_count=unread_count,
    )


@router.post("/{alert_id}/read")
async def mark_alert_read(
    alert_id: str,
    current_user: dict = Depends(require_role("owner", "hr_manager", "consultant")),
) -> dict:
    """Mark a specific alert as read for the current user."""
    user_id = _user_id_from_payload(current_user)
    check_rate_limit(f"mark_alert_read:{user_id}", max_requests=60, window_seconds=60, action_name="mark alert read")
    key = (user_id, alert_id)
    if key not in _alert_status:
        while len(_alert_status) >= _MAX_ALERT_STATUS_ENTRIES:
            _alert_status.popitem(last=False)
    _alert_status[key] = "read"
    _alert_status.move_to_end(key)
    return {"alert_id": alert_id, "status": "read"}


@router.post("/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    current_user: dict = Depends(require_role("owner", "hr_manager", "consultant")),
) -> dict:
    """Dismiss a specific alert for the current user."""
    user_id = _user_id_from_payload(current_user)
    check_rate_limit(f"dismiss_alert:{user_id}", max_requests=60, window_seconds=60, action_name="dismiss alert")
    key = (user_id, alert_id)
    if key not in _alert_status:
        while len(_alert_status) >= _MAX_ALERT_STATUS_ENTRIES:
            _alert_status.popitem(last=False)
    _alert_status[key] = "dismissed"
    _alert_status.move_to_end(key)
    return {"alert_id": alert_id, "status": "dismissed"}


@router.get("/unread-count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: dict = Depends(require_role("owner", "hr_manager", "consultant")),
) -> UnreadCountResponse:
    """Get the number of unread alerts for the current user."""
    user_id = _user_id_from_payload(current_user)
    company_id = current_user.get("company_id")
    raw_alerts = _get_seed_alerts(company_id)
    count = sum(
        1
        for a in raw_alerts
        if _alert_status_for_user(user_id, a["id"]) == "unread"
    )
    return UnreadCountResponse(unread_count=count)


# ── Email delivery for published alerts ─────────────────────


async def notify_users_of_alert(
    alert_title: str,
    alert_description: str,
    source: str = "",
    effective_date: str = "",
    domains: str = "",
) -> int:
    """Send email notifications about a published regulatory alert.

    Attempts to send via the Resend adapter to all users with email
    alerts enabled. Returns the count of emails sent. Fails silently
    (logs errors) to avoid blocking the publish operation.
    """
    import os

    api_key = os.environ.get("RESEND_API_KEY", "")
    if not api_key:
        logger.info("RESEND_API_KEY not configured — skipping alert email delivery")
        return 0

    try:
        from hr_advisory.mcp_servers.adapters.resend_email import ResendAdapter, TEMPLATES
        from hr_advisory.services import dataflow_crud

        adapter = ResendAdapter()

        # Get all active users with email alerts enabled
        users = dataflow_crud.list_records("User", {"is_active": True})
        sent = 0

        for user in users:
            email = user.get("email", "")
            if not email:
                continue

            # Check if user has email alerts enabled (default: True)
            user_id = user.get("id")
            prefs = _notification_prefs.get(user_id, {})
            if not prefs.get("emailAlerts", True):
                continue

            company_name = "your company"
            try:
                if user.get("company_id"):
                    company = dataflow_crud.read("Company", user["company_id"])
                    if company:
                        company_name = company.get("name", company_name)
            except Exception:
                pass

            html = TEMPLATES.get("regulatory_update", "").format(
                update_title=alert_title,
                update_summary=alert_description,
                source=source or "Government Gazette",
                effective_date=effective_date or "See details",
                domains=domains or "Multiple",
                company_name=company_name,
            )

            try:
                await adapter.send_email(
                    to=email,
                    subject=f"Regulatory Alert: {alert_title}",
                    html_body=html,
                )
                sent += 1
            except Exception as exc:
                logger.warning("Failed to send alert email to %s: %s", email, exc)

        logger.info("Alert email delivery: sent=%d, total_users=%d", sent, len(users))
        return sent

    except Exception as exc:
        logger.error("Alert email delivery failed: %s", exc)
        return 0
