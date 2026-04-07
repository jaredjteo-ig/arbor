"""Microsoft Teams adapter for webhook notifications and Adaptive Cards.

Posts notifications via incoming webhooks and builds Adaptive Card JSON
payloads for structured messages (leave approvals, compliance alerts).
Webhook URLs are per-tenant, stored in company settings.

T246: Microsoft Teams Bot Connector (C06)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit

logger = logging.getLogger(__name__)


class TeamsWebhookError(Exception):
    """Raised when a Teams webhook delivery fails."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Teams webhook failed [{status_code}]: {detail}")


class TeamsAdapter:
    """Adapter for Microsoft Teams Incoming Webhooks and Adaptive Cards.

    Uses the Incoming Webhook connector (simplest integration path).
    Each tenant configures their own webhook URL for their Teams channel.
    The adapter builds and sends Adaptive Card payloads.

    For more advanced scenarios (proactive messaging, 1:1 bots), the
    Microsoft Bot Framework / Graph API is needed (see microsoft_graph.py).

    Usage::

        adapter = TeamsAdapter()
        card = adapter.create_adaptive_card(
            title="Leave Approved",
            body="Your annual leave from 15-17 Mar has been approved.",
            actions=[{"title": "View in Arbor", "url": f"{os.environ.get('APP_BASE_URL', 'http://localhost:8000')}/leave"}],
        )
        result = await adapter.send_webhook(webhook_url, card)
    """

    def __init__(self):
        self._circuit = get_circuit("teams")

    @staticmethod
    def create_adaptive_card(
        title: str,
        body: str,
        actions: Optional[list[dict[str, str]]] = None,
        facts: Optional[list[dict[str, str]]] = None,
        color: str = "accent",
    ) -> dict:
        """Build an Adaptive Card JSON payload.

        Adaptive Cards are the standard rich message format for Teams.
        This builds a card following the Adaptive Card schema v1.4.

        Args:
            title: Card title (rendered as a heading).
            body: Main body text (supports basic markdown).
            actions: Optional list of action buttons. Each dict:
                - "title": Button label.
                - "url": URL to open on click.
                Alternatively for message-back actions:
                - "title": Button label.
                - "data": JSON string payload sent back.
            facts: Optional key-value pairs rendered as a fact set.
                Each dict has "title" and "value" keys.
            color: Accent color style: "accent", "good" (green),
                "warning" (amber), "attention" (red).

        Returns:
            Complete Adaptive Card JSON dict ready for webhook posting.
        """
        card_body: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "size": "Medium",
                "weight": "Bolder",
                "text": title,
                "wrap": True,
                "style": "heading",
            },
            {
                "type": "TextBlock",
                "text": body,
                "wrap": True,
            },
        ]

        if facts:
            fact_items = [{"title": f["title"], "value": f["value"]} for f in facts]
            card_body.append(
                {
                    "type": "FactSet",
                    "facts": fact_items,
                }
            )

        card_actions: list[dict[str, Any]] = []
        if actions:
            for action in actions:
                if "url" in action:
                    card_actions.append(
                        {
                            "type": "Action.OpenUrl",
                            "title": action["title"],
                            "url": action["url"],
                        }
                    )
                elif "data" in action:
                    card_actions.append(
                        {
                            "type": "Action.Submit",
                            "title": action["title"],
                            "data": action["data"],
                        }
                    )

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": card_body,
                        "actions": card_actions,
                        "msteams": {
                            "width": "Full",
                        },
                    },
                }
            ],
        }

        return card

    async def send_webhook(
        self,
        webhook_url: str,
        card: dict,
        tenant_id: str = "system",
    ) -> dict:
        """Post an Adaptive Card to a Teams channel via Incoming Webhook.

        Args:
            webhook_url: The Incoming Webhook URL configured for the
                tenant's Teams channel. Stored per-tenant in company
                settings (never hardcoded).
            card: Adaptive Card payload (from create_adaptive_card).
            tenant_id: Tenant ID for logging.

        Returns:
            Dict with status and timestamp.

        Raises:
            TeamsWebhookError: If Teams returns an error.
            ExternalAPIUnavailable: If circuit breaker is open.
        """
        if not webhook_url:
            raise TeamsWebhookError(
                status_code=0,
                detail="No Teams webhook URL configured. Set it in company integration settings.",
            )

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    webhook_url,
                    json=card,
                    headers={"Content-Type": "application/json"},
                )

                # Teams webhooks return 200 with "1" on success, or an
                # error body on failure.
                if resp.status_code >= 400:
                    raise TeamsWebhookError(
                        status_code=resp.status_code,
                        detail=resp.text[:500],
                    )

                return {
                    "status": "sent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "tenant_id": tenant_id,
                }

        result = await self._circuit.call(_do_send)
        logger.info("Teams webhook message sent for tenant %s", tenant_id)
        return result

    # ── Convenience methods for common notifications ─────────────

    async def send_leave_notification(
        self,
        webhook_url: str,
        employee_name: str,
        leave_type: str,
        start_date: str,
        end_date: str,
        status: str,
        approver_name: Optional[str] = None,
        tenant_id: str = "system",
    ) -> dict:
        """Send a leave approval/rejection notification to Teams.

        Args:
            webhook_url: Tenant's Teams webhook URL.
            employee_name: Employee who requested leave.
            leave_type: Type of leave (annual, medical, etc.).
            start_date: Leave start date.
            end_date: Leave end date.
            status: "approved" or "rejected".
            approver_name: Who approved/rejected the leave.
            tenant_id: Tenant ID.
        """
        color = "good" if status == "approved" else "attention"
        title = f"Leave {status.title()}"
        body = f"{employee_name}'s {leave_type} leave request has been {status}."

        facts = [
            {"title": "Employee", "value": employee_name},
            {"title": "Type", "value": leave_type.title()},
            {"title": "Period", "value": f"{start_date} to {end_date}"},
            {"title": "Status", "value": status.title()},
        ]
        if approver_name:
            facts.append({"title": "By", "value": approver_name})

        card = self.create_adaptive_card(
            title=title,
            body=body,
            facts=facts,
            actions=[{"title": "View in Arbor", "url": f"{os.environ.get('APP_BASE_URL', 'http://localhost:8000')}/leave"}],
            color=color,
        )
        return await self.send_webhook(webhook_url, card, tenant_id=tenant_id)

    async def send_payslip_notification(
        self,
        webhook_url: str,
        period: str,
        employee_count: int,
        tenant_id: str = "system",
    ) -> dict:
        """Send a payslip-ready notification to the HR channel.

        Note: No salary amounts or financial data in the message
        (PDPA compliance). Just a notification to view in Arbor.
        """
        card = self.create_adaptive_card(
            title="Payslips Ready",
            body=f"Payslips for {period} have been generated for {employee_count} employees.",
            facts=[
                {"title": "Period", "value": period},
                {"title": "Employees", "value": str(employee_count)},
            ],
            actions=[{"title": "View in Arbor", "url": f"{os.environ.get('APP_BASE_URL', 'http://localhost:8000')}/payroll"}],
        )
        return await self.send_webhook(webhook_url, card, tenant_id=tenant_id)

    async def send_compliance_alert(
        self,
        webhook_url: str,
        alert_title: str,
        alert_body: str,
        severity: str = "warning",
        tenant_id: str = "system",
    ) -> dict:
        """Send a compliance alert to the HR channel."""
        color_map = {"info": "accent", "warning": "warning", "critical": "attention"}
        card = self.create_adaptive_card(
            title=f"Compliance Alert: {alert_title}",
            body=alert_body,
            actions=[{"title": "Review in Arbor", "url": f"{os.environ.get('APP_BASE_URL', 'http://localhost:8000')}/compliance"}],
            color=color_map.get(severity, "warning"),
        )
        return await self.send_webhook(webhook_url, card, tenant_id=tenant_id)
