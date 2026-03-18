"""WhatsApp Cloud API adapter for notification delivery.

Sends approved template messages and interactive messages via Meta's
WhatsApp Cloud API. All templates are notification-only — they direct
the user to "View in Arbor" rather than embedding financial data in
the message body (per red team H4 / PDPA).

T244: WhatsApp Business Connector (C03)
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import get_circuit, RATE_LIMITERS

logger = logging.getLogger(__name__)

_META_GRAPH_BASE = "https://graph.facebook.com/v18.0/"


class WhatsAppTemplate(str, Enum):
    """Pre-approved WhatsApp message templates.

    Each template must be submitted to Meta for review and approval
    before use. Templates are notification-only — they tell the user
    something happened and direct them to Arbor for details.
    """

    PAYSLIP_READY = "payslip_ready"
    LEAVE_APPROVED = "leave_approved"
    LEAVE_REJECTED = "leave_rejected"
    COMPLIANCE_ALERT = "compliance_alert"
    DEADLINE_REMINDER = "deadline_reminder"


# Template body definitions for Meta submission.
# {{1}}, {{2}} etc. are positional parameters filled at send time.
# None of these contain financial data — only references.
TEMPLATE_DEFINITIONS: dict[str, dict[str, Any]] = {
    WhatsAppTemplate.PAYSLIP_READY: {
        "body": "Hi {{1}}, your payslip for {{2}} is ready. View it in Arbor.",
        "parameters": ["employee_name", "period"],
        "category": "UTILITY",
    },
    WhatsAppTemplate.LEAVE_APPROVED: {
        "body": "Hi {{1}}, your leave request for {{2}} to {{3}} has been approved. View details in Arbor.",
        "parameters": ["employee_name", "start_date", "end_date"],
        "category": "UTILITY",
    },
    WhatsAppTemplate.LEAVE_REJECTED: {
        "body": "Hi {{1}}, your leave request for {{2}} to {{3}} was not approved. View details in Arbor.",
        "parameters": ["employee_name", "start_date", "end_date"],
        "category": "UTILITY",
    },
    WhatsAppTemplate.COMPLIANCE_ALERT: {
        "body": "Compliance alert for {{1}}: {{2}}. Please review in Arbor.",
        "parameters": ["company_name", "alert_summary"],
        "category": "UTILITY",
    },
    WhatsAppTemplate.DEADLINE_REMINDER: {
        "body": "Reminder for {{1}}: {{2}} is due on {{3}}. Take action in Arbor.",
        "parameters": ["company_name", "task_description", "due_date"],
        "category": "UTILITY",
    },
}


class WhatsAppDeliveryError(Exception):
    """Raised when WhatsApp message delivery fails."""

    def __init__(self, phone: str, error_code: Optional[int], detail: str):
        self.phone = phone
        self.error_code = error_code
        self.detail = detail
        super().__init__(f"WhatsApp delivery failed for {phone}: [{error_code}] {detail}")


class WhatsAppAdapter:
    """Adapter for Meta WhatsApp Cloud API.

    Supports two message types:
    1. Template messages — pre-approved by Meta, can be sent any time.
       Used for outbound notifications (payslip, leave, compliance).
    2. Interactive messages — freeform with buttons, only within a
       24-hour customer service window (customer must have messaged first).

    All messages go through the circuit breaker and rate limiter.

    Usage::

        adapter = WhatsAppAdapter()
        result = await adapter.send_template(
            phone="+6591234567",
            template_name="payslip_ready",
            parameters=["John Tan", "March 2026"],
        )
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
    ):
        self._access_token = access_token or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self._phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self._circuit = get_circuit("whatsapp")
        self._rate_limiter = RATE_LIMITERS.get("whatsapp")

        if not self._access_token:
            logger.warning("WHATSAPP_ACCESS_TOKEN not set — WhatsApp adapter will fail on send")
        if not self._phone_number_id:
            logger.warning("WHATSAPP_PHONE_NUMBER_ID not set — WhatsApp adapter will fail on send")

    @property
    def _messages_url(self) -> str:
        return f"{_META_GRAPH_BASE}{self._phone_number_id}/messages"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _check_rate_limit(self, tenant_id: str) -> None:
        """Check rate limit before sending. Raises if over limit."""
        if self._rate_limiter and not self._rate_limiter.check(tenant_id, "whatsapp"):
            raise WhatsAppDeliveryError(
                phone="",
                error_code=429,
                detail="Rate limit exceeded for WhatsApp API. Try again shortly.",
            )

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize a phone number for WhatsApp API.

        WhatsApp requires numbers in international format without + or
        leading zeros: e.g., 6591234567 for a Singapore number.
        """
        cleaned = phone.strip().replace(" ", "").replace("-", "")
        if cleaned.startswith("+"):
            cleaned = cleaned[1:]
        # If it looks like a local SG number (8 digits starting with 6/8/9),
        # prepend country code 65.
        if len(cleaned) == 8 and cleaned[0] in ("6", "8", "9"):
            cleaned = f"65{cleaned}"
        return cleaned

    async def send_template(
        self,
        phone: str,
        template_name: str,
        parameters: list[str],
        language_code: str = "en",
        tenant_id: str = "system",
    ) -> dict:
        """Send a pre-approved WhatsApp template message.

        Template messages can be sent at any time (no 24-hour window
        restriction). They must be approved by Meta before use.

        Args:
            phone: Recipient phone number (any format, will be normalized).
            template_name: One of the WhatsAppTemplate enum values.
            parameters: Positional parameters to fill in the template body.
            language_code: Template language code (default "en").
            tenant_id: Tenant ID for rate limiting and audit.

        Returns:
            Dict with message_id and status from WhatsApp API.

        Raises:
            WhatsAppDeliveryError: If the API returns an error.
            ExternalAPIUnavailable: If the circuit breaker is open.
        """
        self._check_rate_limit(tenant_id)
        normalized_phone = self.normalize_phone(phone)

        # Validate template name
        template_def = TEMPLATE_DEFINITIONS.get(template_name)
        if template_def is None:
            valid = ", ".join(TEMPLATE_DEFINITIONS.keys())
            raise WhatsAppDeliveryError(
                phone=normalized_phone,
                error_code=None,
                detail=f"Unknown template '{template_name}'. Valid templates: {valid}",
            )

        # Validate parameter count
        expected_count = len(template_def["parameters"])
        if len(parameters) != expected_count:
            raise WhatsAppDeliveryError(
                phone=normalized_phone,
                error_code=None,
                detail=(
                    f"Template '{template_name}' expects {expected_count} parameters "
                    f"({', '.join(template_def['parameters'])}), got {len(parameters)}"
                ),
            )

        # Build the template message payload per Cloud API spec
        components = []
        if parameters:
            body_params = [{"type": "text", "text": str(p)} for p in parameters]
            components.append({"type": "body", "parameters": body_params})

        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components,
            },
        }

        result = await self._send(payload)
        logger.info(
            "WhatsApp template '%s' sent to %s (msg_id=%s)",
            template_name,
            normalized_phone,
            result.get("message_id", "unknown"),
        )
        return result

    async def send_interactive(
        self,
        phone: str,
        body: str,
        buttons: list[dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None,
        tenant_id: str = "system",
    ) -> dict:
        """Send an interactive message with action buttons.

        Interactive messages can only be sent within a 24-hour customer
        service window — the customer must have messaged the business
        number first. Use this for approve/reject flows where the user
        has already initiated a conversation.

        IMPORTANT: Do not include financial data (salary, CPF amounts,
        bank details) in the body text — PDPA compliance.

        Args:
            phone: Recipient phone number.
            body: Message body text (no PII/financial data).
            buttons: List of button dicts with "id" and "title" keys.
                Maximum 3 buttons, title max 20 characters.
            header: Optional header text (max 60 chars).
            footer: Optional footer text (max 60 chars).
            tenant_id: Tenant ID for rate limiting.

        Returns:
            Dict with message_id and status.

        Raises:
            WhatsAppDeliveryError: If outside 24hr window or API error.
        """
        self._check_rate_limit(tenant_id)
        normalized_phone = self.normalize_phone(phone)

        if len(buttons) > 3:
            raise WhatsAppDeliveryError(
                phone=normalized_phone,
                error_code=None,
                detail="WhatsApp interactive messages support a maximum of 3 buttons",
            )

        for btn in buttons:
            if len(btn.get("title", "")) > 20:
                raise WhatsAppDeliveryError(
                    phone=normalized_phone,
                    error_code=None,
                    detail=f"Button title exceeds 20 character limit: '{btn.get('title', '')}'",
                )

        action_buttons = [
            {"type": "reply", "reply": {"id": btn["id"], "title": btn["title"]}} for btn in buttons
        ]

        interactive: dict[str, Any] = {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": action_buttons},
        }
        if header:
            interactive["header"] = {"type": "text", "text": header[:60]}
        if footer:
            interactive["footer"] = {"text": footer[:60]}

        payload = {
            "messaging_product": "whatsapp",
            "to": normalized_phone,
            "type": "interactive",
            "interactive": interactive,
        }

        result = await self._send(payload)
        logger.info(
            "WhatsApp interactive sent to %s with %d buttons (msg_id=%s)",
            normalized_phone,
            len(buttons),
            result.get("message_id", "unknown"),
        )
        return result

    async def _send(self, payload: dict) -> dict:
        """Send a message via the WhatsApp Cloud API through the circuit breaker.

        Returns a dict with at minimum:
            - message_id: The WhatsApp message ID
            - status: "sent" or error details

        Raises:
            WhatsAppDeliveryError: On API-level error.
            ExternalAPIUnavailable: If circuit breaker is open.
        """

        async def _do_send() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    self._messages_url,
                    json=payload,
                    headers=self._headers(),
                )

                body = resp.json()

                # WhatsApp API returns errors in a specific format
                if resp.status_code >= 400 or "error" in body:
                    error_info = body.get("error", {})
                    raise WhatsAppDeliveryError(
                        phone=payload.get("to", "unknown"),
                        error_code=error_info.get("code"),
                        detail=error_info.get("message", resp.text),
                    )

                # Extract message ID from successful response
                messages = body.get("messages", [])
                message_id = messages[0]["id"] if messages else "unknown"

                return {
                    "message_id": message_id,
                    "status": "sent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "phone": payload.get("to"),
                }

        return await self._circuit.call(_do_send)

    def get_template_info(self, template_name: str) -> Optional[dict]:
        """Get template definition and parameter info.

        Useful for the shadow agent to understand what parameters
        are needed before sending a notification.
        """
        defn = TEMPLATE_DEFINITIONS.get(template_name)
        if defn is None:
            return None
        return {
            "name": template_name,
            "body": defn["body"],
            "parameters": defn["parameters"],
            "category": defn["category"],
        }

    def list_templates(self) -> list[dict]:
        """List all available WhatsApp templates with their parameters."""
        return [
            {
                "name": name,
                "body": defn["body"],
                "parameters": defn["parameters"],
                "category": defn["category"],
            }
            for name, defn in TEMPLATE_DEFINITIONS.items()
        ]
